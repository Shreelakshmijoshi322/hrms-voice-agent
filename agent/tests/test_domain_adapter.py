import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from hr_voice_agent.access import Actor, Role
from hr_voice_agent.action_store import ActionStore
from hr_voice_agent.domain_adapter import EmployeeDomainAdapter, HRAdminDomainAdapter
from hr_voice_agent.fixtures import FixtureRepository
from hr_voice_agent.hrms import HRMSService


class RoleAwareDomainAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = datetime(2026, 8, 13, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        fixtures = FixtureRepository()
        store = ActionStore(Path(self.temp.name) / "demo.sqlite", now=lambda: self.now)
        service = HRMSService(fixtures, store, now=lambda: self.now)
        self.employee = EmployeeDomainAdapter(
            Actor("EMP-1042", Role.EMPLOYEE), service
        )
        self.hr = HRAdminDomainAdapter(Actor("HR-2001", Role.HR_ADMIN), service)

    def test_employee_gets_grounded_conversation_gap_answers(self):
        self.assertEqual(self.employee.get_company_overview()["headcount"], 248)
        self.assertEqual(
            self.employee.get_manager_contact()["work_email"],
            "jordan.lee@people.demo",
        )
        self.assertEqual(
            self.employee.get_calendar_event("weekly sync")["id"], "EVT-1408"
        )
        self.assertEqual(self.employee.get_latest_payslip()["net_pay"], 150000)
        self.assertEqual(self.employee.get_holiday_calendar()[0]["date"], "2026-08-15")
        self.assertGreaterEqual(len(self.employee.get_hr_contacts()), 2)

    def test_leave_date_without_year_uses_next_future_occurrence(self):
        result = self.employee.prepare_leave_request("08-14", "08-20", "vacation")

        self.assertEqual(result["start_date"], "2026-08-14")
        self.assertEqual(result["end_date"], "2026-08-20")
        self.assertTrue(result["requires_confirmation"])

    def test_domain_validation_returns_actionable_result_not_exception(self):
        result = self.employee.prepare_leave_request(
            "2025-08-14", "2025-08-20", "vacation"
        )

        self.assertEqual(result["status"], "invalid")
        self.assertIn("past", result["message"])

    def test_employee_can_update_allowed_profile_field_after_confirmation(self):
        prepared = self.employee.prepare_profile_update("preferred_name", "Maya Joshi")

        blocked = self.employee.execute_pending_action(
            prepared["pending_id"], confirmed=False
        )
        updated = self.employee.execute_pending_action(
            prepared["pending_id"], confirmed=True
        )

        self.assertEqual(blocked["status"], "confirmation_required")
        self.assertEqual(updated["value"], "Maya Joshi")
        self.assertEqual(self.employee.get_my_profile()["preferred_name"], "Maya Joshi")

    def test_cross_session_request_and_hr_approval(self):
        prepared = self.employee.prepare_leave_request("08-14", "08-20", "vacation")
        submitted = self.employee.execute_pending_action(
            prepared["pending_id"], confirmed=True
        )

        queue = self.hr.list_pending_leave_requests()
        self.assertEqual(queue[0]["request_id"], submitted["request_id"])

        decision = self.hr.prepare_leave_decision(
            submitted["request_id"], "approved", "Coverage confirmed"
        )
        approved = self.hr.execute_pending_action(
            decision["pending_id"], confirmed=True
        )

        self.assertEqual(approved["status"], "approved")

    def test_hr_can_update_work_profile_but_employee_cannot(self):
        rejected = self.employee.prepare_profile_update("title", "Lead Designer")
        prepared = self.hr.prepare_employee_profile_update(
            "EMP-1042", "title", "Lead Product Designer"
        )
        updated = self.hr.execute_pending_action(prepared["pending_id"], confirmed=True)

        self.assertEqual(rejected["status"], "invalid")
        self.assertEqual(updated["field"], "title")


if __name__ == "__main__":
    unittest.main()
