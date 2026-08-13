import unittest
from datetime import date

from hr_voice_agent.dates import DateResolutionError, resolve_date_input


class DateResolutionTests(unittest.TestCase):
    def test_month_day_resolves_to_next_future_occurrence(self):
        self.assertEqual(
            resolve_date_input("08-14", date(2026, 8, 13)),
            date(2026, 8, 14),
        )

    def test_passed_month_day_rolls_to_next_year(self):
        self.assertEqual(
            resolve_date_input("08-12", date(2026, 8, 13)),
            date(2027, 8, 12),
        )

    def test_explicit_past_year_is_rejected(self):
        with self.assertRaisesRegex(DateResolutionError, "past"):
            resolve_date_input("2025-08-14", date(2026, 8, 13))


if __name__ == "__main__":
    unittest.main()
