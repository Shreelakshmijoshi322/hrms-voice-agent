import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from hr_voice_agent.access import Actor, PermissionDeniedError, Role
from hr_voice_agent.action_store import ActionStore
from hr_voice_agent.fixtures import FixtureRepository
from hr_voice_agent.hrms import HRMSService


class HRMSServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = datetime(2026, 8, 13, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        self.employee_actor = Actor("EMP-1042", Role.EMPLOYEE)
        self.hr_actor = Actor("HR-2001", Role.HR_ADMIN)
        self.service = HRMSService(
            FixtureRepository(),
            ActionStore(Path(self.temp.name) / "demo.sqlite", now=lambda: self.now),
            now=lambda: self.now,
        )

    def test_employee_cannot_use_hr_leave_queue(self):
        with self.assertRaises(PermissionDeniedError):
            self.service.list_pending_leave_requests(self.employee_actor)

    def test_hr_can_search_the_employee_directory(self):
        result = self.service.search_employee_directory(self.hr_actor, "Jordan")

        self.assertEqual(result[0]["employee_id"], "EMP-1007")
        self.assertEqual(result[0]["work_email"], "jordan.lee@people.demo")

    def test_employee_reads_are_scoped_to_the_actor(self):
        profile = self.service.get_employee_profile(self.employee_actor)

        self.assertEqual(profile["employee_id"], "EMP-1042")
        self.assertEqual(profile["manager"]["employee_id"], "EMP-1007")
        self.assertNotIn("bank_account", profile)

    def test_reports_current_bengaluru_time(self):
        result = self.service.get_current_local_time(self.employee_actor)

        self.assertEqual(result["timezone"], "Asia/Kolkata")
        self.assertEqual(result["date"], "2026-08-13")
        self.assertEqual(result["time"], "10:00")


if __name__ == "__main__":
    unittest.main()
