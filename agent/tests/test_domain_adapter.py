import unittest
from datetime import date

from hr_voice_agent.domain_adapter import HRMSDomainAdapter
from hr_voice_agent.hrms import HRMSService


class HRMSDomainAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        service = HRMSService(today=lambda: date(2026, 8, 13))
        self.adapter = HRMSDomainAdapter(service)

    def test_read_tool_returns_grounded_employee_data(self) -> None:
        result = self.adapter.get_leave_balance()

        self.assertEqual(result["vacation_days"], 12)
        self.assertEqual(result["employee_id"], "EMP-1042")

    def test_prepare_tool_returns_confirmation_without_changing_state(self) -> None:
        result = self.adapter.prepare_leave_request(
            start_date="2026-09-14",
            end_date="2026-09-15",
            leave_type="vacation",
        )

        self.assertTrue(result["requires_confirmation"])
        self.assertEqual(result["days"], 2)
        self.assertRegex(result["pending_id"], r"^pending-")
        self.assertEqual(
            result["confirmation_prompt"],
            "Please confirm: submit your vacation leave request from 2026-09-14 "
            "through 2026-09-15 for 2 days?",
        )
        self.assertNotIn("request_id", result)

    def test_submit_tool_requires_explicit_boolean_confirmation(self) -> None:
        pending = self.adapter.prepare_leave_request(
            start_date="2026-09-14",
            end_date="2026-09-15",
            leave_type="vacation",
        )

        rejected = self.adapter.submit_leave_request(
            pending_id=pending["pending_id"], confirmed=False
        )
        submitted = self.adapter.submit_leave_request(
            pending_id=pending["pending_id"], confirmed=True
        )

        self.assertEqual(rejected["status"], "confirmation_required")
        self.assertEqual(submitted["status"], "submitted")
        self.assertEqual(submitted["request_id"], "LR-1007")


if __name__ == "__main__":
    unittest.main()
