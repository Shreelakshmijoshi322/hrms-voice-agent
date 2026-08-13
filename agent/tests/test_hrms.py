import unittest
from datetime import date, datetime, timedelta, timezone

from hr_voice_agent.hrms import HRMSService, LeaveRequestError


class HRMSServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = HRMSService(today=lambda: date(2026, 8, 13))

    def test_returns_fictional_employee_leave_balance(self) -> None:
        balance = self.service.get_leave_balance("EMP-1042")

        self.assertEqual(
            balance,
            {
                "employee_id": "EMP-1042",
                "vacation_days": 12,
                "sick_days": 7,
                "personal_days": 3,
            },
        )

    def test_returns_employee_profile_without_sensitive_fields(self) -> None:
        profile = self.service.get_employee_profile("EMP-1042")

        self.assertEqual(profile["name"], "Maya Patel")
        self.assertEqual(profile["role"], "Product Designer")
        self.assertEqual(profile["manager"], "Jordan Lee")
        self.assertNotIn("bank_account", profile)

    def test_returns_latest_payslip_summary(self) -> None:
        payslip = self.service.get_latest_payslip("EMP-1042")

        self.assertEqual(payslip["period"], "July 2026")
        self.assertEqual(payslip["status"], "Paid")
        self.assertEqual(payslip["pay_date"], "2026-07-31")

    def test_policy_search_returns_grounded_remote_work_summary(self) -> None:
        result = self.service.search_hr_policy("Can I work remotely?")

        self.assertEqual(result["policy"], "Hybrid & Remote Work")
        self.assertIn("three days per week", result["summary"])

    def test_leave_request_cannot_execute_without_confirmation(self) -> None:
        pending = self.service.prepare_leave_request(
            employee_id="EMP-1042",
            start_date="2026-09-14",
            end_date="2026-09-15",
            leave_type="vacation",
        )

        with self.assertRaisesRegex(LeaveRequestError, "explicit confirmation"):
            self.service.submit_leave_request(pending.id, confirmed=False)

    def test_confirmed_leave_request_is_submitted_once(self) -> None:
        pending = self.service.prepare_leave_request(
            employee_id="EMP-1042",
            start_date="2026-09-14",
            end_date="2026-09-15",
            leave_type="vacation",
        )

        submitted = self.service.submit_leave_request(pending.id, confirmed=True)

        self.assertEqual(submitted.status, "submitted")
        self.assertEqual(submitted.request_id, "LR-1007")
        with self.assertRaisesRegex(LeaveRequestError, "not found or expired"):
            self.service.submit_leave_request(pending.id, confirmed=True)

    def test_rejects_leave_request_that_starts_in_the_past(self) -> None:
        with self.assertRaisesRegex(LeaveRequestError, "future date"):
            self.service.prepare_leave_request(
                employee_id="EMP-1042",
                start_date="2026-08-12",
                end_date="2026-08-14",
                leave_type="vacation",
            )

    def test_rejects_leave_request_with_reversed_dates(self) -> None:
        with self.assertRaisesRegex(LeaveRequestError, "end date"):
            self.service.prepare_leave_request(
                employee_id="EMP-1042",
                start_date="2026-09-15",
                end_date="2026-09-14",
                leave_type="vacation",
            )

    def test_cancel_clears_pending_leave_request(self) -> None:
        pending = self.service.prepare_leave_request(
            employee_id="EMP-1042",
            start_date="2026-09-14",
            end_date="2026-09-15",
            leave_type="vacation",
        )

        self.assertTrue(self.service.cancel_leave_request(pending.id))
        with self.assertRaisesRegex(LeaveRequestError, "not found or expired"):
            self.service.submit_leave_request(pending.id, confirmed=True)

    def test_new_leave_request_replaces_the_previous_pending_request(self) -> None:
        first = self.service.prepare_leave_request(
            employee_id="EMP-1042",
            start_date="2026-09-14",
            end_date="2026-09-15",
            leave_type="vacation",
        )
        second = self.service.prepare_leave_request(
            employee_id="EMP-1042",
            start_date="2026-10-01",
            end_date="2026-10-01",
            leave_type="personal",
        )

        with self.assertRaisesRegex(LeaveRequestError, "not found or expired"):
            self.service.submit_leave_request(first.id, confirmed=True)
        self.assertEqual(
            self.service.submit_leave_request(second.id, confirmed=True).leave_type,
            "personal",
        )

    def test_pending_leave_request_expires(self) -> None:
        clock = [datetime(2026, 8, 13, 9, 0, tzinfo=timezone.utc)]
        service = HRMSService(
            today=lambda: date(2026, 8, 13),
            now=lambda: clock[0],
            pending_ttl=timedelta(minutes=2),
        )
        pending = service.prepare_leave_request(
            employee_id="EMP-1042",
            start_date="2026-09-14",
            end_date="2026-09-15",
            leave_type="vacation",
        )

        clock[0] += timedelta(minutes=3)

        with self.assertRaisesRegex(LeaveRequestError, "not found or expired"):
            service.submit_leave_request(pending.id, confirmed=True)


if __name__ == "__main__":
    unittest.main()
