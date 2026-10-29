from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Callable, Sequence
from zoneinfo import ZoneInfo

from livekit.agents import Agent, RunContext, function_tool

from .access import Actor, Role
from .action_store import ActionStore
from .domain_adapter import EmployeeDomainAdapter, HRAdminDomainAdapter
from .fixtures import FixtureRepository
from .hrms import HRMSService
from .hrms_backend import HRMSBackend, HRMSBackendError


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
        "yes approve",
        "yes update it",
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


def _instructions(actor: Actor, now: Callable[[], datetime]) -> str:
    current = now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
    current = current.astimezone(ZoneInfo("Asia/Kolkata"))
    role_label = "employee self-service" if actor.role is Role.EMPLOYEE else "HR administration"
    return f"""
You are MY ASSISTANT, a warm and concise {role_label} voice assistant for a fictional HRMS demo.
Today is {current.date().isoformat()} in Asia/Kolkata. If the user omits a year, pass dates to tools as MM-DD. If the user states a year, pass YYYY-MM-DD exactly. Never invent a year.
Use tools for every company or employee fact. Describe tool validation messages directly and do not call them technical errors.
You may accept and use a harmless assistant nickname for this session.

Keep replies natural for speech: usually one or two short sentences with no markdown. Never invent a record or claim an action succeeded unless its tool reports success. Do not expose bank data, government identifiers, compensation changes, disciplinary actions, or termination operations.

Understand English and Kannada. Match the user's language on every turn: reply in Kannada when the user speaks Kannada, in English when the user speaks English, and preserve a natural Kannada-English mix when they mix both. Keep names, employee IDs, dates, amounts, and statuses exactly as returned by tools. If the user asks for Kannada, continue in Kannada until they ask for another language.

For an action that returns confirmation_prompt, speak that prompt exactly and alone. Execute it only if the immediately following user turn explicitly confirms; otherwise cancel it or prepare the changed action. All writes are simulated demo changes.
""".strip()


class RoleVoiceAgent(Agent):
    def __init__(
        self,
        actor: Actor,
        adapter: EmployeeDomainAdapter | HRAdminDomainAdapter,
        now: Callable[[], datetime],
    ) -> None:
        self.actor = actor
        self.adapter = adapter
        self.nickname: str | None = None
        super().__init__(instructions=_instructions(actor, now))

    def remember_nickname(self, name: str) -> dict[str, str]:
        nickname = name.strip()
        if not nickname or len(nickname) > 30:
            return {"status": "invalid", "message": "Choose a nickname under 30 characters."}
        self.nickname = nickname
        return {"status": "remembered", "nickname": nickname}

    def _confirmed(self, context: RunContext, pending_id: str) -> bool:
        messages = context.session.history.messages()
        expected = self.adapter.confirmation_prompt_for(pending_id)
        return is_confirmation_exchange(messages, expected)


class EmployeeVoiceAgent(RoleVoiceAgent):
    adapter: EmployeeDomainAdapter

    @function_tool()
    async def set_assistant_nickname(self, name: str) -> dict[str, str]:
        """Use a harmless nickname for this assistant during this voice session."""
        return self.remember_nickname(name)

    @function_tool()
    async def get_my_profile(self) -> dict[str, Any]:
        """Get the signed-in employee's safe work profile."""
        return self.adapter.get_my_profile()

    @function_tool()
    async def get_leave_balance(self) -> dict[str, Any]:
        """Get the employee's vacation, sick, and personal leave balances."""
        return self.adapter.get_leave_balance()

    @function_tool()
    async def get_latest_payslip(self) -> dict[str, Any]:
        """Get the employee's latest fictional payslip and amounts."""
        return self.adapter.get_latest_payslip()

    @function_tool()
    async def get_company_overview(self) -> dict[str, Any]:
        """Get fictional company headcount, departments, and locations."""
        return self.adapter.get_company_overview()

    @function_tool()
    async def get_manager_contact(self) -> dict[str, Any]:
        """Get the employee's manager and work contact details."""
        return self.adapter.get_manager_contact()

    @function_tool()
    async def get_hr_contacts(self) -> list[dict[str, Any]]:
        """Get fictional HR contacts and their support areas."""
        return self.adapter.get_hr_contacts()

    @function_tool()
    async def get_calendar_event(self, query: str) -> dict[str, Any]:
        """Find an event in the employee's demo calendar by topic."""
        return self.adapter.get_calendar_event(query)

    @function_tool()
    async def get_holiday_calendar(self) -> list[dict[str, Any]]:
        """Get upcoming holidays for the employee's location."""
        return self.adapter.get_holiday_calendar()

    @function_tool()
    async def get_current_local_time(self) -> dict[str, str]:
        """Get the current date and time in Asia/Kolkata."""
        return self.adapter.get_current_local_time()

    @function_tool()
    async def get_tasks(self) -> list[dict[str, Any]]:
        """Get the employee's fictional task list."""
        return self.adapter.get_tasks()

    @function_tool()
    async def prioritize_tasks(self) -> list[dict[str, Any]]:
        """Order the employee's tasks by priority and due date."""
        return self.adapter.prioritize_tasks()

    @function_tool()
    async def search_hr_knowledge(self, query: str) -> dict[str, Any]:
        """Search fictional HR policies and learning programs."""
        return self.adapter.search_hr_knowledge(query)

    @function_tool()
    async def prepare_leave_request(
        self, start_date: str, end_date: str, leave_type: str
    ) -> dict[str, Any]:
        """Validate and prepare leave without submitting it."""
        return self.adapter.prepare_leave_request(start_date, end_date, leave_type)

    @function_tool()
    async def prepare_profile_update(self, field: str, value: str) -> dict[str, Any]:
        """Prepare an allowed personal profile update without applying it."""
        return self.adapter.prepare_profile_update(field, value)

    @function_tool()
    async def execute_pending_action(
        self, context: RunContext, pending_id: str
    ) -> dict[str, Any]:
        """Execute a prepared action only after the exact prompt is confirmed."""
        return self.adapter.execute_pending_action(
            pending_id, confirmed=self._confirmed(context, pending_id)
        )

    @function_tool()
    async def cancel_pending_action(self, pending_id: str) -> dict[str, str]:
        """Cancel a pending employee action."""
        return self.adapter.cancel_pending_action(pending_id)


class HRAdminVoiceAgent(RoleVoiceAgent):
    adapter: HRAdminDomainAdapter

    @function_tool()
    async def set_assistant_nickname(self, name: str) -> dict[str, str]:
        """Use a harmless nickname for this assistant during this voice session."""
        return self.remember_nickname(name)

    @function_tool()
    async def get_company_overview(self) -> dict[str, Any]:
        """Get fictional company headcount, departments, and locations."""
        return self.adapter.get_company_overview()

    @function_tool()
    async def search_employee_directory(self, query: str) -> list[dict[str, Any]]:
        """Search the fictional employee directory by work details."""
        return self.adapter.search_employee_directory(query)

    @function_tool()
    async def get_employee_work_profile(self, employee_id: str) -> dict[str, Any]:
        """Get one employee's safe fictional work profile."""
        return self.adapter.get_employee_work_profile(employee_id)

    @function_tool()
    async def get_hr_contacts(self) -> list[dict[str, Any]]:
        """Get fictional HR contacts and support areas."""
        return self.adapter.get_hr_contacts()

    @function_tool()
    async def list_pending_leave_requests(self) -> list[dict[str, Any]]:
        """List leave requests awaiting HR review."""
        return self.adapter.list_pending_leave_requests()

    @function_tool()
    async def prepare_leave_decision(
        self, request_id: str, decision: str, note: str
    ) -> dict[str, Any]:
        """Prepare approval or rejection of a pending leave request."""
        return self.adapter.prepare_leave_decision(request_id, decision, note)

    @function_tool()
    async def prepare_employee_profile_update(
        self, employee_id: str, field: str, value: str
    ) -> dict[str, Any]:
        """Prepare an allowed employee work-profile update."""
        return self.adapter.prepare_employee_profile_update(employee_id, field, value)

    @function_tool()
    async def search_hr_knowledge(self, query: str) -> dict[str, Any]:
        """Search fictional HR policies and learning programs."""
        return self.adapter.search_hr_knowledge(query)

    @function_tool()
    async def get_current_local_time(self) -> dict[str, str]:
        """Get the current date and time in Asia/Kolkata."""
        return self.adapter.get_current_local_time()

    @function_tool()
    async def execute_pending_action(
        self, context: RunContext, pending_id: str
    ) -> dict[str, Any]:
        """Execute a prepared HR action only after exact confirmation."""
        return self.adapter.execute_pending_action(
            pending_id, confirmed=self._confirmed(context, pending_id)
        )

    @function_tool()
    async def cancel_pending_action(self, pending_id: str) -> dict[str, str]:
        """Cancel a pending HR action."""
        return self.adapter.cancel_pending_action(pending_id)


class HRMSBackendVoiceAgent(Agent):
    """Voice shell that delegates HRMS facts and actions to the real AI service."""

    def __init__(self, actor: Actor, backend: HRMSBackend) -> None:
        self.actor = actor
        self.backend = backend
        # Keep the last explicit employee reference so natural follow-ups such
        # as “what is his leave balance?” remain grounded in the same record.
        self._last_employee_reference = ""
        super().__init__(
            instructions=(
                "You are MY ASSISTANT, the authenticated HRMS voice assistant. "
                "For every HRMS question or action, call ask_hrms_backend with the "
                "user's request before answering. Use the backend result as the answer "
                "shown in the transcript and spoken aloud: preserve names, employee "
                "codes, identifiers, dates, amounts, and statuses exactly, and do not "
                "replace a valid result with a generic fallback. Do not invent balances, "
                "policies, dates, or completed actions. Never claim success unless the "
                "backend confirms it. "
                "Understand English and Kannada. Match the user's language on every "
                "turn, replying in Kannada for Kannada input and English for English "
                "input, while allowing a natural Kannada-English mix. Keep names, "
                "employee IDs, dates, amounts, and statuses from the backend exactly. "
                "If asked about authentication, explain that this conversation uses "
                "the employee's already signed-in HRMS session; do not ask them to "
                "log in again unless the backend explicitly reports an authentication "
                "failure. Never describe a normal policy answer as an auth failure. "
                "If the backend reports an error, explain that plainly and suggest "
                "retrying or contacting HR. You may accept a harmless nickname for "
                "this session. Keep spoken replies to one or two short sentences."
            )
        )

    @function_tool()
    async def ask_hrms_backend(self, query: str) -> str:
        """Send the user's HRMS request to the authenticated HRMS AI agent."""
        try:
            cleaned = query.strip()
            lowered = cleaned.casefold()

            # The AI WebSocket is the shared agent runtime used by the Chat UI
            # and LiveKit. Use it first so prompts, tool selection, permissions,
            # conversation context, and the DeepSeek/GLM provider are identical
            # for both input modalities. The deterministic Core reads below are
            # compatibility fallbacks for an unavailable provider/tool gateway.
            try:
                shared_answer = await self.backend.ask(self.actor.session_cookie, cleaned)
                failure_markers = (
                    "failed to process message",
                    "encountered an error",
                    "unable to retrieve",
                    "unable to access",
                    "couldn't retrieve",
                    "authentication required",
                )
                if shared_answer.strip() and not any(
                    marker in shared_answer.casefold() for marker in failure_markers
                ):
                    return shared_answer
            except HRMSBackendError:
                pass

            if (
                ("employee" in lowered or "person" in lowered)
                and any(marker in lowered for marker in ("find", "search", "locate", "look"))
            ) or HRMSBackend._employee_code_from_speech(cleaned):
                try:
                    answer = await self.backend.ask_employee_search(self.actor.session_cookie, cleaned)
                    self._last_employee_reference = cleaned
                    return answer
                except Exception:
                    # Preserve the normal AI path if the direct Core read is
                    # unavailable for this session or deployment.
                    pass
            # Read-only reference data should not depend on model tool
            # selection. These calls use the same authenticated Core session
            # as the HRMS portal and therefore return the exact visible data.
            if "policy" in lowered and any(
                marker in lowered for marker in ("remote", "work from home", "wfh", "explain", "tell")
            ):
                try:
                    return await self.backend.ask_policy(self.actor.session_cookie, cleaned)
                except Exception:
                    pass
            if any(marker in lowered for marker in ("leave balance", "leave balances", "leaves remaining", "leave days", "days remaining")):
                try:
                    return await self.backend.ask_leave_balance(
                        self.actor.session_cookie,
                        cleaned,
                        self._last_employee_reference,
                    )
                except Exception:
                    pass
            if (
                "pending" in lowered
                and any(marker in lowered for marker in ("leave", "casual", "request", "list"))
            ):
                try:
                    return await self.backend.ask_pending_leave_requests(
                        self.actor.session_cookie,
                        cleaned,
                    )
                except Exception:
                    pass
            if "manager" in lowered and any(marker in lowered for marker in ("how many", "count", "number", "present", "organization", "organisation")):
                try:
                    return await self.backend.ask_manager_count(self.actor.session_cookie)
                except Exception:
                    pass
            if any(marker in lowered for marker in ("gross salary", "gross salaries", "salary of", "salary for")):
                try:
                    return await self.backend.ask_salary(
                        self.actor.session_cookie,
                        cleaned,
                        self._last_employee_reference,
                    )
                except Exception:
                    pass
            # Department listing is deterministic and read-only. Bypass a GLM
            # turn so provider 429/529 errors cannot hide valid Core data.
            if "department" in lowered and any(
                marker in lowered for marker in ("what", "which", "list", "all", "there")
            ):
                try:
                    return await self.backend.ask_departments(self.actor.session_cookie)
                except HRMSBackendError:
                    # Preserve the normal AI path if the direct Core read is
                    # unavailable for this session or deployment.
                    return await self.backend.ask(self.actor.session_cookie, cleaned)
            # The shared call above may have failed transiently. Retry it once
            # after deterministic fallbacks so a recovered provider still gets
            # the canonical shared-agent response.
            return await self.backend.ask(self.actor.session_cookie, cleaned)
        except HRMSBackendError as exc:
            return str(exc)


def create_voice_agent(
    actor: Actor,
    fixtures: FixtureRepository,
    store: ActionStore,
    now: Callable[[], datetime] | None = None,
    backend: HRMSBackend | None = None,
) -> EmployeeVoiceAgent | HRAdminVoiceAgent | HRMSBackendVoiceAgent:
    if backend is not None and actor.session_cookie:
        return HRMSBackendVoiceAgent(actor, backend)
    now_provider = now or (lambda: datetime.now(ZoneInfo("Asia/Kolkata")))
    service = HRMSService(fixtures, store, now=now_provider)
    if actor.role is Role.EMPLOYEE:
        return EmployeeVoiceAgent(
            actor, EmployeeDomainAdapter(actor, service), now_provider
        )
    return HRAdminVoiceAgent(actor, HRAdminDomainAdapter(actor, service), now_provider)


# Backward-compatible import for integrations that still reference the original name.
HRMSVoiceAgent = EmployeeVoiceAgent
