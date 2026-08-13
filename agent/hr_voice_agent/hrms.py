from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Callable
from uuid import uuid4


class LeaveRequestError(ValueError):
    """Raised when a simulated leave request cannot be completed."""


@dataclass(frozen=True)
class PendingLeaveRequest:
    id: str
    employee_id: str
    start_date: str
    end_date: str
    leave_type: str
    days: int
    created_at: datetime


@dataclass(frozen=True)
class SubmittedLeaveRequest:
    request_id: str
    status: str
    employee_id: str
    start_date: str
    end_date: str
    leave_type: str


class HRMSService:
    """Deterministic, in-memory HRMS adapter for the voice demo."""

    def __init__(
        self,
        today: Callable[[], date] = date.today,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        pending_ttl: timedelta = timedelta(minutes=2),
    ) -> None:
        self._today = today
        self._now = now
        self._pending_ttl = pending_ttl
        self._pending: dict[str, PendingLeaveRequest] = {}
        self._next_request_number = 1007

    def get_employee_profile(self, employee_id: str) -> dict[str, str]:
        self._require_employee(employee_id)
        return {
            "employee_id": "EMP-1042",
            "name": "Maya Patel",
            "role": "Product Designer",
            "department": "Product & Design",
            "manager": "Jordan Lee",
            "location": "Bengaluru",
        }

    def get_leave_balance(self, employee_id: str) -> dict[str, int | str]:
        self._require_employee(employee_id)
        return {
            "employee_id": "EMP-1042",
            "vacation_days": 12,
            "sick_days": 7,
            "personal_days": 3,
        }

    def get_latest_payslip(self, employee_id: str) -> dict[str, str]:
        self._require_employee(employee_id)
        return {
            "employee_id": "EMP-1042",
            "period": "July 2026",
            "pay_date": "2026-07-31",
            "status": "Paid",
            "currency": "INR",
        }

    def search_hr_policy(self, query: str) -> dict[str, str]:
        normalized = query.casefold()
        if any(term in normalized for term in ("remote", "hybrid", "home")):
            return {
                "policy": "Hybrid & Remote Work",
                "summary": (
                    "Employees may work remotely up to three days per week with "
                    "manager approval. Tuesday and Thursday are team collaboration days."
                ),
            }
        if any(term in normalized for term in ("leave", "vacation", "holiday")):
            return {
                "policy": "Time Off",
                "summary": (
                    "Planned vacation should be requested at least five working days "
                    "in advance and requires manager approval."
                ),
            }
        return {
            "policy": "Human Resources Support",
            "summary": (
                "This topic is not included in the demo policy library. Please contact "
                "a human HR representative for guidance."
            ),
        }

    def prepare_leave_request(
        self,
        *,
        employee_id: str,
        start_date: str,
        end_date: str,
        leave_type: str,
    ) -> PendingLeaveRequest:
        self._require_employee(employee_id)
        try:
            starts = date.fromisoformat(start_date)
            ends = date.fromisoformat(end_date)
        except ValueError as error:
            raise LeaveRequestError("Leave dates must use YYYY-MM-DD format.") from error

        if starts <= self._today():
            raise LeaveRequestError("The leave start date must be a future date.")
        if ends < starts:
            raise LeaveRequestError("The leave end date cannot be before the start date.")

        normalized_type = leave_type.strip().casefold()
        if normalized_type not in {"vacation", "sick", "personal"}:
            raise LeaveRequestError("Leave type must be vacation, sick, or personal.")

        pending = PendingLeaveRequest(
            id=f"pending-{uuid4().hex}",
            employee_id=employee_id,
            start_date=starts.isoformat(),
            end_date=ends.isoformat(),
            leave_type=normalized_type,
            days=(ends - starts).days + 1,
            created_at=self._now(),
        )
        self._pending.clear()
        self._pending[pending.id] = pending
        return pending

    def submit_leave_request(
        self, pending_id: str, *, confirmed: bool
    ) -> SubmittedLeaveRequest:
        pending = self._get_pending(pending_id)
        if pending is None:
            raise LeaveRequestError("The pending leave request was not found or expired.")
        if not confirmed:
            raise LeaveRequestError("Leave submission requires explicit confirmation.")

        del self._pending[pending_id]
        request_id = f"LR-{self._next_request_number}"
        self._next_request_number += 1
        return SubmittedLeaveRequest(
            request_id=request_id,
            status="submitted",
            employee_id=pending.employee_id,
            start_date=pending.start_date,
            end_date=pending.end_date,
            leave_type=pending.leave_type,
        )

    def cancel_leave_request(self, pending_id: str) -> bool:
        if self._get_pending(pending_id) is None:
            return False
        return self._pending.pop(pending_id, None) is not None

    def get_pending_leave_request(self, pending_id: str) -> PendingLeaveRequest:
        pending = self._get_pending(pending_id)
        if pending is None:
            raise LeaveRequestError("The pending leave request was not found or expired.")
        return pending

    def _get_pending(self, pending_id: str) -> PendingLeaveRequest | None:
        pending = self._pending.get(pending_id)
        if pending is None:
            return None
        if self._now() - pending.created_at > self._pending_ttl:
            del self._pending[pending_id]
            return None
        return pending

    @staticmethod
    def _require_employee(employee_id: str) -> None:
        if employee_id != "EMP-1042":
            raise KeyError(f"Employee {employee_id!r} was not found.")
