import unittest

from livekit.agents.llm import ChatMessage

from hr_voice_agent.domain_adapter import HRMSDomainAdapter
from hr_voice_agent.voice_agent import (
    HRMSVoiceAgent,
    is_confirmation_exchange,
    is_explicit_confirmation,
)


class HRMSVoiceAgentTests(unittest.TestCase):
    def test_accepts_only_clear_confirmation_language(self) -> None:
        for phrase in ("Yes, submit it.", "Confirm", "Go ahead", "Please submit"):
            with self.subTest(phrase=phrase):
                self.assertTrue(is_explicit_confirmation(phrase))

        for phrase in ("maybe", "not yet", "don't submit", "what dates?"):
            with self.subTest(phrase=phrase):
                self.assertFalse(is_explicit_confirmation(phrase))

    def test_registers_only_the_seven_supported_hrms_tools(self) -> None:
        agent = HRMSVoiceAgent(HRMSDomainAdapter())

        self.assertEqual(
            sorted(tool.id for tool in agent.tools),
            [
                "cancel_leave_request",
                "get_employee_profile",
                "get_latest_payslip",
                "get_leave_balance",
                "prepare_leave_request",
                "search_hr_policy",
                "submit_leave_request",
            ],
        )

    def test_confirmation_must_immediately_answer_the_exact_action_prompt(self) -> None:
        expected = (
            "Please confirm: submit your vacation leave request from 2026-09-14 "
            "through 2026-09-15 for 2 days?"
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
                    ChatMessage(
                        role="assistant",
                        content=["I did not submit your leave. Can you confirm which leave policy you mean?"],
                    ),
                    ChatMessage(role="user", content=["Yes"]),
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
        mismatched = expected.replace("2026-09-15", "2026-09-16")
        self.assertFalse(
            is_confirmation_exchange(
                [
                    ChatMessage(role="assistant", content=[mismatched]),
                    ChatMessage(role="user", content=["Yes"]),
                ],
                expected,
            )
        )


if __name__ == "__main__":
    unittest.main()
