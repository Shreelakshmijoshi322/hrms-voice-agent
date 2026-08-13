# Role-Aware HRMS Assistant Expansion Design

Date: 2026-08-13
Status: Approved for implementation planning

## Purpose

Expand the working LiveKit HRMS voice demo from one narrowly scoped employee assistant into a useful role-aware HRMS assistant. The expanded demo must provide grounded answers for the gaps observed during live testing and offer separate Employee and HR Admin experiences with enforced tool permissions.

The assistant remains the product focus. Dashboard work is limited to demo login, role-adaptive content, and the controls needed to demonstrate assistant capabilities.

## Approved Demo Accounts

- Employee: `maya@people.demo` / `employee123`
- HR Admin: `priya@people.demo` / `hradmin123`

These accounts are fictional, local to the demo, and not suitable for production authentication.

## Chosen Architecture

Use one Next.js application, one LiveKit worker, and one shared HRMS domain layer. The authenticated role determines dashboard content, participant attributes, agent instructions, and registered tools.

This is preferred over separate employee and HR applications because it preserves the existing reusable voice layer and avoids duplicated interface and worker code. It is preferred over prompt-only permissions because authorization must not depend on model compliance.

## Authentication and Role Propagation

1. The login endpoint validates one of the two fixed demo accounts.
2. A successful login creates a signed, HTTP-only session cookie containing the fictional user ID and role.
3. Server-rendered pages and data endpoints validate the session before returning role-specific information.
4. The LiveKit token endpoint ignores client-supplied identity and role values. It reads the trusted session and adds user ID and role as participant attributes.
5. The Python worker reads those attributes and constructs the correct role-specific agent and tool registry.
6. Logout ends the active voice session and clears the session cookie.

Employees cannot access HR tools even if the model attempts to call one. HR users receive only the administrative tools included in this design.

## Role-Adaptive Interface

The existing application shell remains shared.

Employee mode shows Maya's profile, leave balance, payslip, tasks, calendar, holidays, and employee-focused suggested prompts.

HR Admin mode shows Priya's identity, workforce summary, employee search, HR contacts, pending leave requests, and administrative suggested prompts. The voice panel remains visually consistent in both modes while its greeting, examples, and capabilities change by role.

The login page displays both demo accounts so the experience is easy to demonstrate. It also clearly labels the authentication and data as simulated.

## Fictional Data Model

Readable JSON fixtures provide deterministic source data for:

- Company profile and total headcount.
- Department headcounts and office locations.
- A small employee directory with safe work email and extension fields.
- HR representatives and escalation contacts.
- Employee profiles and reporting relationships.
- Leave balances and leave policies.
- Payslip gross pay, deductions, net pay, currency, period, and status.
- Holiday dates and applicable locations.
- Calendar events, including Design Weekly Sync descriptions.
- Employee tasks with priority, due date, and status.
- Learning programs, workshops, and enrollment details.
- A broader HR policy library.

SQLite stores simulated mutable state shared across local worker processes:

- Prepared and submitted leave requests.
- HR approval or rejection decisions.
- Approved safe employee profile changes.

Fixture data can be reset deterministically for tests and demonstrations. No real employee information is used.

## Employee Assistant Capabilities

The Employee Assistant can:

- Retrieve the signed-in employee's full safe profile.
- Retrieve vacation, sick, and personal leave balances.
- Prepare, confirm, submit, and cancel a leave request.
- Retrieve a detailed payslip breakdown.
- Explain personal calendar events.
- Retrieve location-specific holiday information.
- List and prioritize the employee's tasks.
- Search policies and learning programs.
- Retrieve company summary, manager work contact, and HR support contacts.
- Update approved profile fields such as preferred name, phone, and work location after confirmation.
- Accept and remember an assistant nickname, such as Jay, for the current session only.

The Employee Assistant cannot see another employee's private profile, payslip, leave balance, or task list.

## HR Admin Assistant Capabilities

The HR Admin Assistant can:

- Retrieve workforce and department summaries.
- Search the fictional employee directory.
- Retrieve safe employee work profiles and contacts.
- Retrieve HR team and office contact information.
- List pending leave requests.
- Prepare and confirm leave approval or rejection.
- Prepare and confirm permitted employee work-profile updates.
- Search the full policy, holiday, calendar, and learning-program fixtures.

Administrative writes require explicit confirmation and return a simulated audit identifier. Payroll changes, legal decisions, disciplinary actions, termination, bank data, government identifiers, and other sensitive operations remain out of scope.

## Date and Time Behavior

The agent receives the current date and `Asia/Kolkata` timezone in its session instructions.

- A month and day without a year resolves to the next future occurrence.
- A weekday-only request asks for a specific date.
- An ambiguous range asks one concise follow-up question.
- The agent can report the current local date and time.
- Domain validation returns an actionable result rather than throwing an exception into tool execution.

This corrects the observed behavior where August 2026 requests were incorrectly converted to August 2025.

## Conversation Behavior

- Responses remain short and natural for speech.
- The assistant uses tools for all employee, company, calendar, task, policy, and payroll facts.
- Unsupported questions receive a clear capability explanation without repeatedly escalating to HR.
- A user-selected assistant nickname is session-scoped and does not alter authorization or persisted data.
- Tool errors produce specific recovery guidance.
- Turn endpointing tolerates normal short pauses so one sentence is not split into multiple committed turns.
- Interruption handling resists brief background noise while retaining intentional barge-in.

## Confirmation and Safety

Every simulated write uses a structured pending action containing the acting user, target record, exact proposed change, creation time, and deterministic confirmation prompt.

The immediately following user message must explicitly confirm the exact pending action. Pending actions expire, are replaced when details change, and are consumed after execution. Role checks are repeated inside the write operation.

The model cannot supply a boolean that bypasses confirmation.

## Failure Handling

- Invalid login returns a generic authentication error.
- Missing or invalid sessions redirect to login and cannot mint a LiveKit token.
- Missing data returns a grounded not-found result.
- Invalid dates explain the required correction.
- Tool and storage errors return a safe, actionable failure response and never claim success.
- Provider failures retain the existing safe voice-service recovery behavior.
- Unexpected room disconnects retain the existing restart path.

## Testing

Automated coverage includes:

- Both demo logins and invalid credentials.
- Signed session validation, logout, and role-specific token attributes.
- Role-filtered tool registration and direct authorization checks.
- Expanded company, directory, contact, holiday, calendar, task, learning, payslip, and policy queries.
- Current-date injection and future-year date resolution.
- Structured domain errors for invalid dates.
- Employee leave submission followed by HR approval in a separate session.
- Safe profile update confirmation and forbidden-field rejection.
- Nickname memory within one session and reset in a new session.
- Exact confirmation adjacency, mismatch, expiry, replacement, and single-use behavior.
- Role-adaptive dashboard content and login/logout flows.
- Turn-handling configuration intended to reduce fragmented input and false interruptions.

Manual verification covers Employee login, grounded questions, leave submission, logout, HR login, viewing the same request, approving it, and hearing the confirmed status as an employee.

## Acceptance Criteria

- The two demo accounts open distinct Employee and HR Admin experiences.
- The LiveKit worker derives role and identity from trusted server-issued attributes.
- Employee and HR tool permissions are enforced in code.
- The assistant answers the expanded scenarios from deterministic fictional data.
- Dates without a year resolve correctly relative to the current date.
- Leave requests no longer fail with unhandled domain exceptions.
- An employee request is visible and actionable in a later HR session.
- Administrative and employee writes require exact explicit confirmation.
- The assistant can use a session nickname chosen by the user.
- The employee and HR dashboards reuse the same voice-session and assistant-panel components.
- Automated tests and the production build pass.

## Non-Goals

- Production authentication or a real user database.
- Integration with a real HRMS, payroll, calendar, email, or directory provider.
- Real personal data or persistent production records.
- General internet browsing by the voice agent.
- High-risk HR actions such as termination, compensation modification, or disciplinary decisions.
