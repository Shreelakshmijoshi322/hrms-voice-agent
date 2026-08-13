import unittest

from hr_voice_agent.fixtures import FixtureRepository


class FixtureRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.repo = FixtureRepository()

    def test_exposes_conversation_gap_data(self):
        self.assertEqual(self.repo.company()["headcount"], 248)
        self.assertEqual(self.repo.employee("EMP-1042")["manager_id"], "EMP-1007")
        self.assertEqual(self.repo.payslip("EMP-1042")["net_pay"], 150000)
        self.assertIn("Design Weekly Sync", self.repo.calendar("EMP-1042")[0]["title"])
        self.assertEqual(self.repo.holidays("Bengaluru")[0]["date"], "2026-08-15")
        self.assertGreaterEqual(len(self.repo.hr_contacts()), 2)


if __name__ == "__main__":
    unittest.main()
