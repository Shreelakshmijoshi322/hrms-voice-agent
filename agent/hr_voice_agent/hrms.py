from __future__ import annotations

from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

from .access import Actor, Role, require_role
from .action_store import ActionStore
from .dates import DateResolutionError, resolve_date_input
from .fixtures import FixtureNotFoundError, FixtureRepository


class HRMSValidationError(ValueError):
    pass


class LeaveRequestError(HRMSValidationError):
    """Compatibility name for leave-specific validation errors."""


class HRMSService:
    """Role-enforced domain service over fictional fixtures and SQLite demo state."""

    EMPLOYEE_PROFILE_FIELDS = {"preferred_name", "phone", "location"}
    HR_PROFILE_FIELDS = EMPLOYEE_PROFILE_FIELDS | {
        "title",
        "department",
        "manager_id",
    }

    def __init__(
        self,
        fixtures: FixtureRepository | None = None,
        store: ActionStore | None = None,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.fixtures = fixtures or FixtureRepository()
        self.store = store or ActionStore()
        self._now_provider = now or (lambda: datetime.now(ZoneInfo("Asia/Kolkata")))

    def _now(self) -> datetime:
        value = self._now_provider()
        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
        return value.astimezone(ZoneInfo("Asia/Kolkata"))

    def _employee_record(self, employee_id: str) -> dict[str, Any]:
        record = dict(self.fixtures.employee(employee_id))
        record.update(self.store.get_profile_overrides(employee_id))
        return record

    def get_employee_profile(self, actor: Actor) -> dict[str, Any]:
        require_role(actor, Role.EMPLOYEE)
        profile = self._employee_record(actor.user_id)
        profile["manager"] = self._employee_record(profile["manager_id"])
        return profile

    def get_leave_balance(self, actor: Actor) -> dict[str, Any]:
        require_role(actor, Role.EMPLOYEE)
        return {
            "employee_id": actor.user_id,
            **self.fixtures.leave_balance(actor.user_id),
        }

    def get_latest_payslip(self, actor: Actor) -> dict[str, Any]:
        require_role(actor, Role.EMPLOYEE)
        return {"employee_id": actor.user_id, **self.fixtures.payslip(actor.user_id)}

    def get_company_overview(self, actor: Actor) -> dict[str, Any]:
        require_role(actor, Role.EMPLOYEE, Role.HR_ADMIN)
        return self.fixtures.company()

    def get_manager_contact(self, actor: Actor) -> dict[str, Any]:
        require_role(actor, Role.EMPLOYEE)
        employee = self._employee_record(actor.user_id)
        return self._employee_record(employee["manager_id"])

    def get_hr_contacts(self, actor: Actor) -> list[dict[str, Any]]:
        require_role(actor, Role.EMPLOYEE, Role.HR_ADMIN)
        contacts: list[dict[str, Any]] = []
        for contact in self.fixtures.hr_contacts():
            employee = self._employee_record(contact["employee_id"])
            contacts.append({**employee, **contact})
        return contacts

    def get_calendar_event(self, actor: Actor, query: str) -> dict[str, Any]:
        require_role(actor, Role.EMPLOYEE)
        needle = query.casefold()
        for event in self.fixtures.calendar(actor.user_id):
            searchable = f"{event['title']} {event['description']}".casefold()
            if all(part in searchable for part in needle.split()):
                return event
        raise FixtureNotFoundError("No matching event was found in your demo calendar.")

    def get_holiday_calendar(self, actor: Actor) -> list[dict[str, Any]]:
        require_role(actor, Role.EMPLOYEE)
        employee = self._employee_record(actor.user_id)
        return self.fixtures.holidays(employee["location"])

    def get_tasks(self, actor: Actor) -> list[dict[str, Any]]:
        require_role(actor, Role.EMPLOYEE)
        return self.fixtures.tasks(actor.user_id)

    def prioritize_tasks(self, actor: Actor) -> list[dict[str, Any]]:
        priorities = {"high": 0, "medium": 1, "low": 2}
        return sorted(
            self.get_tasks(actor),
            key=lambda item: (priorities[item["priority"]], item["due_date"]),
        )

    def search_hr_knowledge(self, actor: Actor, query: str) -> dict[str, Any]:
        require_role(actor, Role.EMPLOYEE, Role.HR_ADMIN)
        policies = self.fixtures.search(query)
        programs = [
            program
            for program in self.fixtures.learning_programs()
            if query.casefold() in f"{program['name']} {program['format']} {program['eligibility']}".casefold()
        ]
        return {"policies": policies, "learning_programs": programs}

    def get_current_local_time(self, actor: Actor) -> dict[str, str]:
        require_role(actor, Role.EMPLOYEE, Role.HR_ADMIN)
        current = self._now()
        return {
            "timezone": "Asia/Kolkata",
            "date": current.date().isoformat(),
            "time": current.strftime("%H:%M"),
        }

    def search_employee_directory(
        self, actor: Actor, query: str
    ) -> list[dict[str, Any]]:
        require_role(actor, Role.HR_ADMIN)
        needle = query.casefold().strip()
        return [
            self._employee_record(employee["employee_id"])
            for employee in self.fixtures.employees()
            if needle
            in " ".join(
                str(employee[field])
                for field in ("name", "title", "department", "location", "work_email")
            ).casefold()
        ]

    def get_employee_work_profile(
        self, actor: Actor, employee_id: str
    ) -> dict[str, Any]:
        require_role(actor, Role.HR_ADMIN)
        return self._employee_record(employee_id)

    def prepare_leave_request(
        self,
        actor: Actor,
        start_date: str,
        end_date: str,
        leave_type: str,
    ) -> dict[str, Any]:
        require_role(actor, Role.EMPLOYEE)
        try:
            starts = resolve_date_input(start_date, self._now().date())
            ends = resolve_date_input(end_date, self._now().date())
        except DateResolutionError as error:
            raise LeaveRequestError(str(error)) from error
        if ends < starts:
            raise LeaveRequestError("The leave end date cannot be before the start date.")
        normalized_type = leave_type.strip().casefold()
        balance = self.fixtures.leave_balance(actor.user_id)
        if normalized_type not in balance:
            raise LeaveRequestError("Leave type must be vacation, sick, or personal.")
        days = (ends - starts).days + 1
        if days > balance[normalized_type]:
            raise LeaveRequestError(
                f"You have only {balance[normalized_type]} {normalized_type} days available."
            )
        day_label = "day" if days == 1 else "days"
        prompt = (
            f"Please confirm: submit your {normalized_type} leave request from "
            f"{starts.isoformat()} through {ends.isoformat()} for {days} {day_label}?"
        )
        pending = self.store.prepare_action(
            actor_id=actor.user_id,
            action_type="leave_request",
            payload={
                "employee_id": actor.user_id,
                "start_date": starts.isoformat(),
                "end_date": ends.isoformat(),
                "leave_type": normalized_type,
                "days": days,
            },
            prompt=prompt,
        )
        return {
            **pending.payload,
            "pending_id": pending.id,
            "requires_confirmation": True,
            "confirmation_prompt": prompt,
        }

    def prepare_profile_update(
        self,
        actor: Actor,
        field: str,
        value: str,
        *,
        employee_id: str | None = None,
    ) -> dict[str, Any]:
        if actor.role is Role.EMPLOYEE:
            allowed = self.EMPLOYEE_PROFILE_FIELDS
            target = actor.user_id
        else:
            require_role(actor, Role.HR_ADMIN)
            allowed = self.HR_PROFILE_FIELDS
            target = employee_id
        if target is None:
            raise HRMSValidationError("Choose an employee before preparing the update.")
        self.fixtures.employee(target)
        if field not in allowed:
            raise HRMSValidationError("That profile field cannot be changed by this role.")
        if not value.strip():
            raise HRMSValidationError("The new profile value cannot be empty.")
        prompt = f"Please confirm: update {field} for {target} to {value.strip()}?"
        pending = self.store.prepare_action(
            actor_id=actor.user_id,
            action_type="profile_update",
            payload={"employee_id": target, "field": field, "value": value.strip()},
            prompt=prompt,
        )
        return {
            "pending_id": pending.id,
            "requires_confirmation": True,
            "confirmation_prompt": prompt,
            **pending.payload,
        }

    def list_pending_leave_requests(self, actor: Actor) -> list[dict[str, Any]]:
        require_role(actor, Role.HR_ADMIN)
        return [
            {
                "request_id": leave.id,
                "employee": self._employee_record(leave.employee_id),
                "employee_id": leave.employee_id,
                "start_date": leave.start_date,
                "end_date": leave.end_date,
                "leave_type": leave.leave_type,
                "days": leave.days,
                "status": leave.status,
            }
            for leave in self.store.list_leave_requests(status="pending_hr")
        ]

    def prepare_leave_decision(
        self,
        actor: Actor,
        request_id: str,
        decision: str,
        note: str,
    ) -> dict[str, Any]:
        require_role(actor, Role.HR_ADMIN)
        normalized = decision.casefold().strip()
        if normalized not in {"approved", "rejected"}:
            raise HRMSValidationError("Decision must be approved or rejected.")
        pending_ids = {
            leave.id for leave in self.store.list_leave_requests(status="pending_hr")
        }
        if request_id not in pending_ids:
            raise HRMSValidationError("That leave request is not pending HR review.")
        prompt = (
            f"Please confirm: mark leave request {request_id} as {normalized}"
            f" with note {note or 'No note'}?"
        )
        pending = self.store.prepare_action(
            actor_id=actor.user_id,
            action_type="leave_decision",
            payload={"request_id": request_id, "decision": normalized, "note": note},
            prompt=prompt,
        )
        return {
            "pending_id": pending.id,
            "requires_confirmation": True,
            "confirmation_prompt": prompt,
            **pending.payload,
        }

    def execute_pending_action(self, actor: Actor, pending_id: str) -> dict[str, Any]:
        require_role(actor, Role.EMPLOYEE, Role.HR_ADMIN)
        return self.store.execute_action(pending_id, actor_id=actor.user_id)

    def cancel_pending_action(self, actor: Actor, pending_id: str) -> None:
        require_role(actor, Role.EMPLOYEE, Role.HR_ADMIN)
        self.store.cancel_action(pending_id, actor_id=actor.user_id)
