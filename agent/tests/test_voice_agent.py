import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from livekit.agents.llm import ChatMessage

from hr_voice_agent.access import Actor, Role
from hr_voice_agent.action_store import ActionStore
from hr_voice_agent.fixtures import FixtureRepository
from hr_voice_agent.voice_agent import (
    create_voice_agent,
    is_confirmation_exchange,
    is_explicit_confirmation,
)


class RoleAwareVoiceAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fixtures = FixtureRepository()
        self.now_value = datetime(
            2026, 8, 13, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata")
        )
        self.now = lambda: self.now_value
        self.store = ActionStore(
            Path(self.temp.name) / "demo.sqlite", now=self.now
        )

    def test_employee_and_hr_agents_register_different_tools(self):
        employee = create_voice_agent(
            Actor("EMP-1042", Role.EMPLOYEE), self.fixtures, self.store, self.now
        )
        hr = create_voice_agent(
            Actor("HR-2001", Role.HR_ADMIN), self.fixtures, self.store, self.now
        )

        employee_tools = {tool.id for tool in employee.tools}
        hr_tools = {tool.id for tool in hr.tools}
        self.assertIn("get_latest_payslip", employee_tools)
        self.assertNotIn("search_employee_directory", employee_tools)
        self.assertIn("search_employee_directory", hr_tools)
        self.assertNotIn("get_latest_payslip", hr_tools)

    def test_instructions_include_current_date_timezone_and_role(self):
        agent = create_voice_agent(
            Actor("EMP-1042", Role.EMPLOYEE),
            self.fixtures,
            self.store,
            self.now,
        )

        self.assertIn("2026-08-13", agent.instructions)
        self.assertIn("Asia/Kolkata", agent.instructions)
        self.assertIn("employee", agent.instructions.casefold())
        self.assertIn("kannada", agent.instructions.casefold())

    def test_nickname_is_session_scoped(self):
        first = create_voice_agent(
            Actor("EMP-1042", Role.EMPLOYEE), self.fixtures, self.store, self.now
        )
        second = create_voice_agent(
            Actor("EMP-1042", Role.EMPLOYEE), self.fixtures, self.store, self.now
        )

        self.assertEqual(first.remember_nickname("Jay")["nickname"], "Jay")
        self.assertIsNone(second.nickname)

    def test_accepts_only_clear_confirmation_language(self):
        for phrase in ("Yes, submit it.", "Confirm", "Go ahead", "Please submit"):
            with self.subTest(phrase=phrase):
                self.assertTrue(is_explicit_confirmation(phrase))

        for phrase in ("maybe", "not yet", "don't submit", "what dates?"):
            with self.subTest(phrase=phrase):
                self.assertFalse(is_explicit_confirmation(phrase))

    def test_confirmation_must_immediately_answer_the_exact_action_prompt(self):
        expected = (
            "Please confirm: submit your vacation leave request from 2026-08-14 "
            "through 2026-08-20 for 7 days?"
        )
        self.assertTrue(
            is_confirmation_exchange(
                [
                    ChatMessage(role="assistant", content=[expected]),
                    ChatMessage(role="user", content=["Yes, submit it."]),
                ],
                expected,
            )
        )
        self.assertFalse(
            is_confirmation_exchange(
                [
                    ChatMessage(role="assistant", content=[expected]),
                    ChatMessage(role="user", content=["What dates did I say?"]),
                    ChatMessage(role="user", content=["Yes"]),
                ],
                expected,
            )
        )


if __name__ == "__main__":
    unittest.main()
