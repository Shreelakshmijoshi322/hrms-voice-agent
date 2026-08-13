from __future__ import annotations

from typing import Any

from .access import Actor, Role
from .action_store import ActionStoreError
from .fixtures import FixtureNotFoundError
from .hrms import HRMSService, HRMSValidationError


def _invalid(error: Exception) -> dict[str, str]:
    return {"status": "invalid", "message": str(error)}


class EmployeeDomainAdapter:
    def __init__(self, actor: Actor, service: HRMSService) -> None:
        self.actor = actor
        self._service = service
        self._confirmation_prompts: dict[str, str] = {}

    def get_my_profile(self) -> dict[str, Any]:
        return self._service.get_employee_profile(self.actor)

    def get_leave_balance(self) -> dict[str, Any]:
        return self._service.get_leave_balance(self.actor)

    def get_latest_payslip(self) -> dict[str, Any]:
        return self._service.get_latest_payslip(self.actor)

    def get_company_overview(self) -> dict[str, Any]:
        return self._service.get_company_overview(self.actor)

    def get_manager_contact(self) -> dict[str, Any]:
        return self._service.get_manager_contact(self.actor)

    def get_hr_contacts(self) -> list[dict[str, Any]]:
        return self._service.get_hr_contacts(self.actor)

    def get_calendar_event(self, query: str) -> dict[str, Any]:
        try:
            return self._service.get_calendar_event(self.actor, query)
        except FixtureNotFoundError as error:
            return _invalid(error)

    def get_holiday_calendar(self) -> list[dict[str, Any]]:
        return self._service.get_holiday_calendar(self.actor)

    def get_current_local_time(self) -> dict[str, str]:
        return self._service.get_current_local_time(self.actor)

    def get_tasks(self) -> list[dict[str, Any]]:
        return self._service.get_tasks(self.actor)

    def prioritize_tasks(self) -> list[dict[str, Any]]:
        return self._service.prioritize_tasks(self.actor)

    def search_hr_knowledge(self, query: str) -> dict[str, Any]:
        return self._service.search_hr_knowledge(self.actor, query)

    def prepare_leave_request(
        self, start_date: str, end_date: str, leave_type: str
    ) -> dict[str, Any]:
        try:
            result = self._service.prepare_leave_request(
                self.actor, start_date, end_date, leave_type
            )
            self._remember_confirmation(result)
            return result
        except (HRMSValidationError, FixtureNotFoundError) as error:
            return _invalid(error)

    def prepare_profile_update(self, field: str, value: str) -> dict[str, Any]:
        try:
            result = self._service.prepare_profile_update(self.actor, field, value)
            self._remember_confirmation(result)
            return result
        except (HRMSValidationError, FixtureNotFoundError) as error:
            return _invalid(error)

    def execute_pending_action(
        self, pending_id: str, *, confirmed: bool
    ) -> dict[str, Any]:
        if not confirmed:
            return {
                "status": "confirmation_required",
                "message": "Ask the employee to explicitly confirm the exact action.",
            }
        try:
            return self._service.execute_pending_action(self.actor, pending_id)
        except ActionStoreError as error:
            return {"status": "failed", "message": str(error)}

    def cancel_pending_action(self, pending_id: str) -> dict[str, str]:
        try:
            self._service.cancel_pending_action(self.actor, pending_id)
            return {"status": "cancelled", "pending_id": pending_id}
        except ActionStoreError as error:
            return {"status": "failed", "message": str(error)}

    def confirmation_prompt_for(self, pending_id: str) -> str | None:
        return self._confirmation_prompts.get(pending_id)

    def _remember_confirmation(self, result: dict[str, Any]) -> None:
        if "pending_id" in result and "confirmation_prompt" in result:
            self._confirmation_prompts[result["pending_id"]] = result[
                "confirmation_prompt"
            ]


class HRAdminDomainAdapter:
    def __init__(self, actor: Actor, service: HRMSService) -> None:
        self.actor = actor
        self._service = service
        self._confirmation_prompts: dict[str, str] = {}

    def get_company_overview(self) -> dict[str, Any]:
        return self._service.get_company_overview(self.actor)

    def search_employee_directory(self, query: str) -> list[dict[str, Any]]:
        return self._service.search_employee_directory(self.actor, query)

    def get_employee_work_profile(self, employee_id: str) -> dict[str, Any]:
        try:
            return self._service.get_employee_work_profile(self.actor, employee_id)
        except FixtureNotFoundError as error:
            return _invalid(error)

    def get_hr_contacts(self) -> list[dict[str, Any]]:
        return self._service.get_hr_contacts(self.actor)

    def list_pending_leave_requests(self) -> list[dict[str, Any]]:
        return self._service.list_pending_leave_requests(self.actor)

    def prepare_leave_decision(
        self, request_id: str, decision: str, note: str
    ) -> dict[str, Any]:
        try:
            result = self._service.prepare_leave_decision(
                self.actor, request_id, decision, note
            )
            self._remember_confirmation(result)
            return result
        except HRMSValidationError as error:
            return _invalid(error)

    def prepare_employee_profile_update(
        self, employee_id: str, field: str, value: str
    ) -> dict[str, Any]:
        try:
            result = self._service.prepare_profile_update(
                self.actor, field, value, employee_id=employee_id
            )
            self._remember_confirmation(result)
            return result
        except (HRMSValidationError, FixtureNotFoundError) as error:
            return _invalid(error)

    def search_hr_knowledge(self, query: str) -> dict[str, Any]:
        return self._service.search_hr_knowledge(self.actor, query)

    def get_current_local_time(self) -> dict[str, str]:
        return self._service.get_current_local_time(self.actor)

    def execute_pending_action(
        self, pending_id: str, *, confirmed: bool
    ) -> dict[str, Any]:
        if not confirmed:
            return {
                "status": "confirmation_required",
                "message": "Ask the HR administrator to explicitly confirm the exact action.",
            }
        try:
            return self._service.execute_pending_action(self.actor, pending_id)
        except ActionStoreError as error:
            return {"status": "failed", "message": str(error)}

    def cancel_pending_action(self, pending_id: str) -> dict[str, str]:
        try:
            self._service.cancel_pending_action(self.actor, pending_id)
            return {"status": "cancelled", "pending_id": pending_id}
        except ActionStoreError as error:
            return {"status": "failed", "message": str(error)}

    def confirmation_prompt_for(self, pending_id: str) -> str | None:
        return self._confirmation_prompts.get(pending_id)

    def _remember_confirmation(self, result: dict[str, Any]) -> None:
        if "pending_id" in result and "confirmation_prompt" in result:
            self._confirmation_prompts[result["pending_id"]] = result[
                "confirmation_prompt"
            ]


class HRMSDomainAdapter(EmployeeDomainAdapter):
    """Temporary compatibility adapter for the original employee voice agent."""

    def __init__(self, service: HRMSService | None = None) -> None:
        super().__init__(
            Actor("EMP-1042", Role.EMPLOYEE),
            service or HRMSService(),
        )

    def get_employee_profile(self) -> dict[str, Any]:
        return self.get_my_profile()

    def search_hr_policy(self, query: str) -> dict[str, Any]:
        return self.search_hr_knowledge(query)

    def submit_leave_request(
        self, *, pending_id: str, confirmed: bool
    ) -> dict[str, Any]:
        return self.execute_pending_action(pending_id, confirmed=confirmed)

    def cancel_leave_request(self, *, pending_id: str) -> dict[str, str]:
        return self.cancel_pending_action(pending_id)
