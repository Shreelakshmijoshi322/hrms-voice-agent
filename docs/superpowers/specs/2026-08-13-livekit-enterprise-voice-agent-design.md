# LiveKit Enterprise Voice Agent Demo Design

Date: 2026-08-13
Status: Approved for implementation planning

## Purpose

Build a browser-based live voice-agent demo for employee self-service in an HRMS. The HRMS experience is the first domain example, while the LiveKit voice layer and assistant panel remain reusable in similar enterprise applications such as CRM, ERP, helpdesk, and employee portals.

The demo must let an employee speak naturally, receive a low-latency spoken response, follow the live transcript, retrieve fictional employee information, and safely simulate a data-changing action.

## Goals

- Demonstrate a natural two-way voice conversation over LiveKit WebRTC.
- Show clear listening, thinking, speaking, muted, reconnecting, and disconnected states.
- Stream interim and final transcripts into the interface.
- Answer questions about fictional HRMS data and policies.
- Retrieve an employee's leave balance, latest payslip information, profile, and relevant policy content.
- Simulate a leave request only after explicit user confirmation.
- Keep the voice transport and UI shell independent from HR-specific prompts and tools.
- Provide a polished, responsive HRMS-style dashboard suitable for a product demonstration.

## Non-goals

- Connecting to a production HRMS or using real employee data.
- Implementing authentication, authorization, payroll processing, or a complete HRMS.
- Persisting mock changes across application restarts.
- Supporting telephony, outbound calls, video avatars, or multiple agents.
- Building a general-purpose plugin marketplace. Reuse is achieved through small configuration and tool interfaces.

## Chosen Voice Architecture

Use a cascaded speech-to-text, language-model, and text-to-speech pipeline managed by LiveKit Agents.

This approach is preferred over a direct speech-to-speech realtime model because the demo requires immediate transcripts, predictable HRMS tool calls, explicit confirmations, and an inspectable text trail. These qualities matter more than achieving the absolute minimum model latency.

The pipeline consists of:

1. LiveKit transports microphone and agent audio over WebRTC.
2. Speech-to-text produces interim and final user transcripts.
3. The language model generates concise responses or selects a domain tool.
4. Text-to-speech streams the approved response back to the user.

The initial implementation uses LiveKit Inference for all three stages, minimizing the number of credentials required for the demo. The default descriptors are `deepgram/nova-3:en` for STT, `google/gemma-4-31b-it` for the LLM, and `inworld/inworld-tts-2:Ashley` for TTS. Environment variables may override these defaults without modifying domain logic.

## System Architecture

### Web application

A Next.js/React application provides:

- The HRMS dashboard and fictional employee summary.
- A reusable voice-assistant panel.
- LiveKit session connection and microphone controls.
- Agent-state visualization, audio playback, and transcript display.
- A server-only endpoint that creates short-lived, room-scoped LiveKit access tokens.

The browser never receives LiveKit API secrets or model-provider credentials.

### Voice agent

A Python LiveKit Agents service provides:

- The STT-LLM-TTS `AgentSession`.
- Voice-friendly system instructions and response constraints.
- Interruption and turn-handling behavior.
- Domain configuration and tool registration.
- Tool-call confirmation rules.
- Friendly recovery messages for domain failures.

### Mock domain service

An in-process mock HRMS adapter owns fictional employee data and domain operations. It exposes typed, independently testable tools:

- `get_employee_profile`
- `get_leave_balance`
- `get_latest_payslip`
- `search_hr_policy`
- `create_leave_request`

Read operations execute immediately. `create_leave_request` requires an explicit confirmation turn and returns a simulated request identifier on success.

## Reuse Across Enterprise Applications

The system separates generic voice capabilities from domain-specific behavior.

### Generic voice layer

Owns room connection, audio transport, transcript events, interruptions, agent-state mapping, microphone controls, disconnect behavior, and shared error presentation. It has no knowledge of leave, payroll, or employee records.

### Reusable assistant panel

Accepts branding, title, welcome text, suggested prompts, and domain labels as properties or configuration. It can be embedded in another dashboard without changing the LiveKit session code.

### Domain adapter

Provides:

- Agent instructions and vocabulary.
- Suggested prompts.
- Tool definitions and implementations.
- Fixture data for the selected demonstration domain.
- Rules identifying read-only and data-changing operations.

The HRMS adapter is the only adapter delivered in this scope. A future CRM or helpdesk adapter would replace this configuration and tool set while retaining the same LiveKit voice layer and assistant panel.

## User Interface

The dashboard resembles a modern enterprise HRMS and includes:

- Sidebar navigation for Home, Leave, Payroll, Policies, and Profile.
- Employee summary with a fictional name, job title, department, and manager.
- Cards for leave balance, latest payslip, upcoming holiday, and pending requests.
- A prominent voice-assistant panel on the right on desktop and a full-width panel on smaller screens.
- A clear start-session action before microphone permission is requested.
- A compact audio visualizer and textual session state.
- A scrollable transcript with distinct employee and agent messages.
- Microphone mute, retry, and end-session controls.
- Suggested prompts including "Check my leave balance" and "Explain the remote-work policy."

The interface uses semantic controls, visible focus states, keyboard access, sufficient contrast, and reduced-motion-friendly state indicators.

## Agent Behavior

The agent is concise, professional, warm, and suitable for spoken interaction. It follows these rules:

- Use only information returned by the configured domain tools or supplied policy fixtures.
- Never invent employee records, balances, policies, or operation results.
- Ask a short follow-up question when a required tool argument is missing.
- Repeat the important details and request explicit confirmation before any data-changing tool call.
- Treat clear phrases such as "yes, submit it" as confirmation only when they directly follow the confirmation prompt.
- Cancel or revise the pending action when the user declines or changes its details.
- Never claim an operation succeeded unless its tool returned success.
- Direct unsupported, sensitive, or human-judgment matters to a human HR representative.
- Keep spoken responses brief and avoid markdown, dense lists, and unnecessary jargon.

## Primary User Flow

1. The employee opens the dashboard and selects "Talk to HR Assistant."
2. The browser requests microphone permission and requests a short-lived LiveKit session token.
3. The browser connects to the LiveKit room and publishes microphone audio.
4. The agent joins, greets the employee, and enters the listening state.
5. STT interim text is displayed while the employee speaks; the final transcript becomes a conversation message.
6. The model answers directly or calls an HRMS adapter tool.
7. Read-only tool results are summarized in a concise spoken response.
8. A data-changing request is summarized and held pending until the employee confirms it.
9. TTS output is streamed to the browser and the agent message is appended to the transcript.
10. The employee may interrupt the response, mute the microphone, continue the conversation, or end the session.

Example read flow:

> Employee: How many vacation days do I have?
>
> Agent: You have 12 vacation days remaining.

Example write flow:

> Employee: Request vacation for September 14 and 15.
>
> Agent: You want to request two vacation days, September 14 and 15. Should I submit it?
>
> Employee: Yes, submit it.
>
> Agent: Your simulated leave request has been submitted. The request ID is LR-1007.

## State and Data Handling

- Employee and policy fixtures are deterministic local data committed with the demo.
- Mock changes are kept in memory for the current process only.
- Conversation transcripts exist for the active browser session and are not persisted by the application.
- Pending write confirmations are scoped to one agent session and cleared after execution, cancellation, disconnect, or timeout.
- LiveKit and provider observability or retention settings are deployment concerns and must be documented in the setup guide; the application does not promise zero retention on behalf of external services.

## Failure Handling

- Microphone permission denied: explain how to enable access and provide a retry action.
- Token request failed: show a non-sensitive connection error and keep retry available.
- LiveKit disconnected unexpectedly: enter a reconnecting state, rely on supported automatic recovery, and offer a clean restart if recovery fails.
- Agent did not join: time out with a friendly message and allow the session to be restarted.
- STT, LLM, or TTS failure: stop the active response, report that the assistant is temporarily unavailable, and never display raw secrets or provider payloads.
- Domain read failure: state that the information could not be retrieved.
- Domain write failure: state that the action was not completed and preserve no false success state.
- Missing environment configuration: fail startup with a precise list of missing variable names, never their values.

## Security and Privacy Boundaries

- Use only fictional employee and policy data.
- Generate LiveKit access tokens on the server with the minimum room permissions needed for the demo.
- Keep LiveKit API secrets and model-provider credentials in server-side environment variables.
- Do not log access tokens, secrets, raw audio, or full employee conversations in application logs.
- Require explicit confirmation for data-changing tools.
- Validate and normalize all tool arguments before changing mock state.
- Clearly label leave submission as simulated in both the interface and spoken confirmation.

## Testing Strategy

### Unit tests

- Mock HRMS read tools return deterministic data.
- Leave requests validate dates and required fields.
- Data-changing tools cannot run without the confirmation guard.
- Pending confirmation is cleared after success, cancellation, timeout, or disconnect.
- Domain configuration satisfies the generic adapter contract.
- Frontend state mapping renders the expected label and controls.

### Frontend and integration tests

- The dashboard and assistant panel render at desktop and mobile breakpoints.
- Transcript messages preserve speaker identity and final ordering.
- Start, mute, retry, and disconnect controls invoke the expected session actions.
- The token endpoint validates its request and returns only client-safe connection data.
- Agent tool calls receive and return the expected typed payloads.

### Manual end-to-end verification

- Grant and deny microphone permission.
- Start a LiveKit voice session and hear the greeting.
- Observe interim/final transcript behavior and agent-state changes.
- Ask for leave balance, payslip information, and policy content.
- Interrupt the agent while it is speaking.
- Mute and unmute the microphone.
- Confirm and cancel separate simulated leave requests.
- Interrupt the connection and verify recovery or a clear restart path.
- Navigate and operate the assistant with a keyboard.

## Acceptance Criteria

- A user can start and end a LiveKit voice session from the HRMS dashboard.
- User speech produces a visible transcript and an audible agent response.
- The interface accurately represents the agent's connection and speaking state.
- The agent retrieves deterministic fictional HRMS data through tools rather than inventing values.
- The agent supports profile, leave, payslip, and policy questions.
- The agent requires and respects explicit confirmation for simulated leave submission.
- A user can interrupt speech and mute or unmute the microphone.
- Errors are actionable and do not expose secrets or falsely report completed actions.
- The assistant panel and voice-session code contain no HR-specific business logic.
- Tests cover critical domain tools, confirmation behavior, UI session states, and token generation.

## Required Configuration

The implementation will document required environment variables for:

- LiveKit server URL.
- LiveKit API key and secret.

Optional environment variables can override the default LiveKit Inference STT, LLM, TTS, and voice descriptors. The delivered configuration does not require direct provider keys.

An example environment file will include variable names and safe descriptions only.

## Delivery Shape

The repository will contain:

- A Next.js/React web application.
- A Python LiveKit Agents service.
- A reusable assistant panel and generic session layer.
- An HRMS domain adapter with deterministic fixtures.
- Automated tests for the critical frontend and agent behaviors.
- Setup documentation covering credentials, local startup, test commands, and the scripted demo flow.
