from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .hrms import HRMSService, LeaveRequestError


class HRMSDomainAdapter:
    """Voice-friendly tool boundary around an HRMS service."""

    employee_id = "EMP-1042"

    def __init__(self, service: HRMSService | None = None) -> None:
        self._service = service or HRMSService()

    def get_employee_profile(self) -> dict[str, Any]:
        return self._service.get_employee_profile(self.employee_id)

    def get_leave_balance(self) -> dict[str, Any]:
        return self._service.get_leave_balance(self.employee_id)

    def get_latest_payslip(self) -> dict[str, Any]:
        return self._service.get_latest_payslip(self.employee_id)

    def search_hr_policy(self, query: str) -> dict[str, Any]:
        return self._service.search_hr_policy(query)

    def prepare_leave_request(
        self, *, start_date: str, end_date: str, leave_type: str
    ) -> dict[str, Any]:
        pending = self._service.prepare_leave_request(
            employee_id=self.employee_id,
            start_date=start_date,
            end_date=end_date,
            leave_type=leave_type,
        )
        return {
            "pending_id": pending.id,
            "start_date": pending.start_date,
            "end_date": pending.end_date,
            "leave_type": pending.leave_type,
            "days": pending.days,
            "requires_confirmation": True,
            "confirmation_prompt": self._confirmation_prompt(pending),
        }

    def confirmation_prompt_for(self, pending_id: str) -> str | None:
        try:
            pending = self._service.get_pending_leave_request(pending_id)
        except LeaveRequestError:
            return None
        return self._confirmation_prompt(pending)

    def submit_leave_request(self, *, pending_id: str, confirmed: bool) -> dict[str, Any]:
        if not confirmed:
            return {
                "status": "confirmation_required",
                "message": "Ask the employee to explicitly confirm before submitting.",
            }
        try:
            return asdict(
                self._service.submit_leave_request(pending_id, confirmed=True)
            )
        except LeaveRequestError as error:
            return {"status": "failed", "message": str(error)}

    def cancel_leave_request(self, *, pending_id: str) -> dict[str, str]:
        cancelled = self._service.cancel_leave_request(pending_id)
        return {
            "status": "cancelled" if cancelled else "not_found",
            "pending_id": pending_id,
        }

    @staticmethod
    def _confirmation_prompt(pending: Any) -> str:
        day_label = "day" if pending.days == 1 else "days"
        return (
            f"Please confirm: submit your {pending.leave_type} leave request from "
            f"{pending.start_date} through {pending.end_date} for "
            f"{pending.days} {day_label}?"
        )
