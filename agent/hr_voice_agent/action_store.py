from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


class ActionStoreError(RuntimeError):
    """Base error for safe, simulated HRMS writes."""


class ActionNotFoundError(ActionStoreError):
    pass


class ActionAuthorizationError(ActionStoreError):
    pass


class ActionStateError(ActionStoreError):
    pass


@dataclass(frozen=True)
class PendingAction:
    id: str
    actor_id: str
    action_type: str
    payload: dict[str, Any]
    prompt: str
    created_at: str
    expires_at: str
    consumed_at: str | None


@dataclass(frozen=True)
class LeaveRequest:
    id: str
    employee_id: str
    start_date: str
    end_date: str
    leave_type: str
    days: int
    status: str
    decided_by: str | None
    decision_note: str | None
    created_at: str
    decided_at: str | None


class ActionStore:
    def __init__(
        self,
        path: Path | str | None = None,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._path = Path(path or os.getenv("HRMS_DEMO_DB", "agent/data/hrms-demo.sqlite"))
        self._now_provider = now or (lambda: datetime.now(timezone.utc))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS pending_actions (
                  id TEXT PRIMARY KEY,
                  actor_id TEXT NOT NULL,
                  action_type TEXT NOT NULL,
                  payload_json TEXT NOT NULL,
                  prompt TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  expires_at TEXT NOT NULL,
                  consumed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS leave_requests (
                  id TEXT PRIMARY KEY,
                  employee_id TEXT NOT NULL,
                  start_date TEXT NOT NULL,
                  end_date TEXT NOT NULL,
                  leave_type TEXT NOT NULL,
                  days INTEGER NOT NULL,
                  status TEXT NOT NULL,
                  decided_by TEXT,
                  decision_note TEXT,
                  created_at TEXT NOT NULL,
                  decided_at TEXT
                );
                CREATE TABLE IF NOT EXISTS profile_overrides (
                  employee_id TEXT NOT NULL,
                  field TEXT NOT NULL,
                  value TEXT NOT NULL,
                  updated_by TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  PRIMARY KEY (employee_id, field)
                );
                """
            )
        finally:
            connection.close()

    def _now(self) -> datetime:
        current = self._now_provider()
        return current if current.tzinfo else current.replace(tzinfo=timezone.utc)

    def prepare_action(
        self,
        *,
        actor_id: str,
        action_type: str,
        payload: dict[str, Any],
        prompt: str,
    ) -> PendingAction:
        created_at = self._now()
        action = PendingAction(
            id=f"ACT-{uuid.uuid4().hex[:12].upper()}",
            actor_id=actor_id,
            action_type=action_type,
            payload=payload,
            prompt=prompt,
            created_at=created_at.isoformat(),
            expires_at=(created_at + timedelta(minutes=5)).isoformat(),
            consumed_at=None,
        )
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    """
                    INSERT INTO pending_actions
                    (id, actor_id, action_type, payload_json, prompt, created_at, expires_at, consumed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (
                        action.id,
                        action.actor_id,
                        action.action_type,
                        json.dumps(action.payload),
                        action.prompt,
                        action.created_at,
                        action.expires_at,
                    ),
                )
        finally:
            connection.close()
        return action

    def _pending_from_row(self, row: sqlite3.Row) -> PendingAction:
        return PendingAction(
            id=row["id"],
            actor_id=row["actor_id"],
            action_type=row["action_type"],
            payload=json.loads(row["payload_json"]),
            prompt=row["prompt"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            consumed_at=row["consumed_at"],
        )

    def _validate_pending(self, row: sqlite3.Row | None, actor_id: str) -> PendingAction:
        if row is None:
            raise ActionNotFoundError("That pending action was not found.")
        action = self._pending_from_row(row)
        if action.actor_id != actor_id:
            raise ActionAuthorizationError("That pending action belongs to another user.")
        if action.consumed_at is not None:
            raise ActionStateError("That pending action has already been used.")
        if datetime.fromisoformat(action.expires_at) <= self._now():
            raise ActionStateError("That pending action has expired. Please prepare it again.")
        return action

    def confirm_action(self, pending_id: str, *, actor_id: str) -> PendingAction:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM pending_actions WHERE id = ?", (pending_id,)
            ).fetchone()
            return self._validate_pending(row, actor_id)
        finally:
            connection.close()

    def execute_action(self, pending_id: str, *, actor_id: str) -> dict[str, Any]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM pending_actions WHERE id = ?", (pending_id,)
            ).fetchone()
            action = self._validate_pending(row, actor_id)
            result = self._apply_action(connection, action)
            consumed_at = self._now().isoformat()
            connection.execute(
                "UPDATE pending_actions SET consumed_at = ? WHERE id = ?",
                (consumed_at, action.id),
            )
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _apply_action(
        self, connection: sqlite3.Connection, action: PendingAction
    ) -> dict[str, Any]:
        payload = action.payload
        now = self._now().isoformat()
        if action.action_type == "profile_update":
            employee_id = payload.get("employee_id", action.actor_id)
            field = payload["field"]
            value = payload["value"]
            connection.execute(
                """
                INSERT INTO profile_overrides (employee_id, field, value, updated_by, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(employee_id, field) DO UPDATE SET
                  value = excluded.value,
                  updated_by = excluded.updated_by,
                  updated_at = excluded.updated_at
                """,
                (employee_id, field, value, action.actor_id, now),
            )
            return {
                "status": "updated",
                "employee_id": employee_id,
                "field": field,
                "value": value,
            }
        if action.action_type == "leave_request":
            leave = self._insert_leave_request(
                connection,
                payload["employee_id"],
                payload["start_date"],
                payload["end_date"],
                payload["leave_type"],
                int(payload["days"]),
            )
            return {"status": leave.status, "request_id": leave.id}
        if action.action_type == "leave_decision":
            request_id = payload["request_id"]
            decision = payload["decision"]
            cursor = connection.execute(
                """
                UPDATE leave_requests
                SET status = ?, decided_by = ?, decision_note = ?, decided_at = ?
                WHERE id = ? AND status = 'pending_hr'
                """,
                (decision, action.actor_id, payload.get("note", ""), now, request_id),
            )
            if cursor.rowcount != 1:
                raise ActionStateError("That leave request is no longer pending HR review.")
            return {"status": decision, "request_id": request_id}
        raise ActionStateError("That action type is not supported by this demo.")

    def cancel_action(self, pending_id: str, *, actor_id: str) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM pending_actions WHERE id = ?", (pending_id,)
            ).fetchone()
            action = self._validate_pending(row, actor_id)
            connection.execute(
                "UPDATE pending_actions SET consumed_at = ? WHERE id = ?",
                (self._now().isoformat(), action.id),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _insert_leave_request(
        self,
        connection: sqlite3.Connection,
        employee_id: str,
        start_date: str,
        end_date: str,
        leave_type: str,
        days: int,
    ) -> LeaveRequest:
        leave = LeaveRequest(
            id=f"LR-{uuid.uuid4().hex[:10].upper()}",
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            leave_type=leave_type,
            days=days,
            status="pending_hr",
            decided_by=None,
            decision_note=None,
            created_at=self._now().isoformat(),
            decided_at=None,
        )
        connection.execute(
            """
            INSERT INTO leave_requests
            (id, employee_id, start_date, end_date, leave_type, days, status,
             decided_by, decision_note, created_at, decided_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, NULL)
            """,
            (
                leave.id,
                leave.employee_id,
                leave.start_date,
                leave.end_date,
                leave.leave_type,
                leave.days,
                leave.status,
                leave.created_at,
            ),
        )
        return leave

    def create_leave_request(
        self,
        employee_id: str,
        start_date: str,
        end_date: str,
        leave_type: str,
        days: int,
    ) -> LeaveRequest:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            leave = self._insert_leave_request(
                connection, employee_id, start_date, end_date, leave_type, days
            )
            connection.commit()
            return leave
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_leave_requests(self, *, status: str | None = None) -> list[LeaveRequest]:
        connection = self._connect()
        try:
            if status is None:
                rows = connection.execute(
                    "SELECT * FROM leave_requests ORDER BY created_at"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM leave_requests WHERE status = ? ORDER BY created_at",
                    (status,),
                ).fetchall()
            return [LeaveRequest(**dict(row)) for row in rows]
        finally:
            connection.close()

    def get_profile_overrides(self, employee_id: str) -> dict[str, str]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT field, value FROM profile_overrides WHERE employee_id = ?",
                (employee_id,),
            ).fetchall()
            return {row["field"]: row["value"] for row in rows}
        finally:
            connection.close()
