from __future__ import annotations

import re
from typing import Any, Sequence

from livekit.agents import Agent, RunContext, function_tool

from .domain_adapter import HRMSDomainAdapter


AGENT_INSTRUCTIONS = """
You are Ask People, a warm and concise employee self-service voice assistant.

You help Maya Patel with the fictional HRMS data available through your tools. Use a
tool for employee-specific facts, payslips, balances, policies, and leave requests.
Never invent a record or claim an action succeeded unless its tool reports success.

Keep replies natural for speech: usually one or two short sentences, with no markdown,
emoji, or dense lists. Ask one short follow-up question when required information is
missing. For unsupported, sensitive, legal, disciplinary, or human-judgment matters,
say that a human HR representative should help.

Leave submission is a simulated data-changing action. First call
prepare_leave_request. Its result contains confirmation_prompt. Speak that prompt
exactly, with nothing before or after it. Only when the employee's immediately following
turn explicitly confirms may you call submit_leave_request, and do not speak a preamble
before that tool call. If the employee declines or changes details, cancel the pending
request or prepare a replacement. Always describe a successful request as simulated.
""".strip()


def is_explicit_confirmation(text: str) -> bool:
    normalized = re.sub(r"[^a-z\s]", "", text.casefold()).strip()
    if any(negation in normalized.split() for negation in ("no", "not", "dont", "cancel")):
        return False
    return normalized in {
        "yes",
        "yes submit",
        "yes submit it",
        "confirm",
        "confirmed",
        "go ahead",
        "please submit",
        "please submit it",
        "submit",
        "submit it",
    }


def is_confirmation_exchange(
    messages: Sequence[Any], expected_prompt: str | None
) -> bool:
    """Require an exact prompt followed immediately by an explicit user confirmation."""
    if expected_prompt is None or len(messages) < 2:
        return False
    prompt_message, user_message = messages[-2:]
    if prompt_message.role != "assistant" or user_message.role != "user":
        return False
    actual_prompt = " ".join((prompt_message.text_content or "").split()).casefold()
    required_prompt = " ".join(expected_prompt.split()).casefold()
    return actual_prompt == required_prompt and is_explicit_confirmation(
        user_message.text_content or ""
    )


class HRMSVoiceAgent(Agent):
    def __init__(self, adapter: HRMSDomainAdapter | None = None) -> None:
        self._adapter = adapter or HRMSDomainAdapter()
        super().__init__(instructions=AGENT_INSTRUCTIONS)

    @function_tool()
    async def get_employee_profile(self) -> dict[str, Any]:
        """Get the current employee's safe profile details."""
        return self._adapter.get_employee_profile()

    @function_tool()
    async def get_leave_balance(self) -> dict[str, Any]:
        """Get the current employee's vacation, sick, and personal leave balances."""
        return self._adapter.get_leave_balance()

    @function_tool()
    async def get_latest_payslip(self) -> dict[str, Any]:
        """Get the period, pay date, and status of the latest fictional payslip."""
        return self._adapter.get_latest_payslip()

    @function_tool()
    async def search_hr_policy(self, query: str) -> dict[str, Any]:
        """Search the demo HR policy library.

        Args:
            query: The employee's policy topic or question.
        """
        return self._adapter.search_hr_policy(query)

    @function_tool()
    async def prepare_leave_request(
        self, start_date: str, end_date: str, leave_type: str
    ) -> dict[str, Any]:
        """Validate and prepare a leave request without submitting it.

        Args:
            start_date: First leave date in YYYY-MM-DD format.
            end_date: Final leave date in YYYY-MM-DD format.
            leave_type: One of vacation, sick, or personal.
        """
        return self._adapter.prepare_leave_request(
            start_date=start_date,
            end_date=end_date,
            leave_type=leave_type,
        )

    @function_tool()
    async def submit_leave_request(
        self, context: RunContext, pending_id: str
    ) -> dict[str, Any]:
        """Submit a prepared request only after the latest user turn clearly confirms it.

        Args:
            pending_id: Identifier returned by prepare_leave_request.
        """
        messages = context.session.history.messages()
        expected_prompt = self._adapter.confirmation_prompt_for(pending_id)
        return self._adapter.submit_leave_request(
            pending_id=pending_id,
            confirmed=is_confirmation_exchange(messages, expected_prompt),
        )

    @function_tool()
    async def cancel_leave_request(self, pending_id: str) -> dict[str, str]:
        """Cancel a prepared request when the employee declines or changes it.

        Args:
            pending_id: Identifier returned by prepare_leave_request.
        """
        return self._adapter.cancel_leave_request(pending_id=pending_id)
