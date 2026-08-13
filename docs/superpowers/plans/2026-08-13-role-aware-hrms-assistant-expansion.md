# Role-Aware HRMS Assistant Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the LiveKit HRMS demo into a grounded, role-aware Employee and HR Admin voice assistant with shared fictional data, reliable date handling, and confirmed cross-session actions.

**Architecture:** A signed demo session in Next.js determines dashboard content and trusted LiveKit participant attributes. The Python worker creates either an employee or HR agent from those attributes; both use a fixture repository for reads and a process-safe SQLite action store for simulated writes. Authorization and confirmation are enforced in the domain layer, not by prompts.

**Tech Stack:** Next.js 16.3, React 19, TypeScript 5.9, `jose`, LiveKit React Components, Python 3.12, LiveKit Agents 1.6, SQLite, Vitest, Testing Library, Python `unittest`.

## Global Constraints

- Keep both accounts and every HRMS record fictional and clearly labelled as demo data.
- Employee credentials are `maya@people.demo` / `employee123`; HR Admin credentials are `priya@people.demo` / `hradmin123`.
- Use `Asia/Kolkata` for employee-facing dates and time.
- The browser must never choose its own identity, role, room, or agent dispatch name.
- Enforce role permissions and exact write confirmation inside Python domain code.
- Keep dashboard changes secondary to assistant capability; reuse the existing voice session and panel.
- Never allow payroll mutation, bank data, government identifiers, termination, disciplinary action, or compensation modification.
- Read the installed Next.js 16 guides under `node_modules/next/dist/docs/` before editing cookies, route handlers, or server/client boundaries.

---

### Task 1: Preserve the Verified Demo Baseline

**Files:**
- Modify: `.gitignore`
- Track: `AGENTS.md`, `CLAUDE.md`, `.env.example`, `package.json`, `package-lock.json`, `tsconfig.json`, `vitest.config.ts`, `next-env.d.ts`, `app/**`, `web/**`, `agent/**`

**Interfaces:**
- Consumes: the currently verified untracked implementation.
- Produces: a clean Git baseline from which later task commits contain reviewable diffs.

- [ ] **Step 1: Ignore generated brainstorming and runtime database files**

Add these exact lines to `.gitignore`:

```gitignore
.superpowers/
agent/data/*.sqlite
agent/data/*.sqlite-shm
agent/data/*.sqlite-wal
```

- [ ] **Step 2: Verify the existing implementation before checkpointing it**

Run:

```bash
npm run test:all
npm run typecheck
npm run build
PYTHONPATH=agent .venv/bin/python agent/agent.py --help
git diff --check
```

Expected: 15 web tests and 19 Python tests pass, type checking and build exit 0, the LiveKit CLI help loads, and the diff check is empty.

- [ ] **Step 3: Commit only project source and generated Next agent rules**

```bash
git add .gitignore AGENTS.md CLAUDE.md .env.example package.json package-lock.json tsconfig.json vitest.config.ts next-env.d.ts app web agent
git commit -m "feat: add LiveKit HRMS voice agent demo"
```

Expected: `.env.local`, `.venv`, `.next`, and `.superpowers` remain untracked or ignored.

---

### Task 2: Add Grounded Fictional Fixtures and Date Resolution

**Files:**
- Create: `data/hrms-fixtures.json`
- Create: `agent/hr_voice_agent/fixtures.py`
- Create: `agent/hr_voice_agent/dates.py`
- Create: `agent/tests/test_fixtures.py`
- Create: `agent/tests/test_dates.py`

**Interfaces:**
- Produces: `FixtureRepository(path: Path | None = None)`, `FixtureRepository.employee(employee_id)`, `FixtureRepository.search(query)`, and `resolve_date_input(value: str, today: date) -> date`.
- Consumes: no later-task interfaces.

- [ ] **Step 1: Write failing fixture and date tests**

```python
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
```

- [ ] **Step 2: Run the new tests and confirm missing-module failures**

Run:

```bash
PYTHONPATH=agent .venv/bin/python -m unittest agent.tests.test_fixtures agent.tests.test_dates -v
```

Expected: FAIL because `fixtures` and `dates` do not exist.

- [ ] **Step 3: Add the complete deterministic fixture**

The JSON must contain these top-level keys and exact stable identifiers:

```json
{
  "company": {
    "name": "People Demo Technologies",
    "headcount": 248,
    "departments": {"Product & Design": 42, "Engineering": 96, "Sales": 54, "Operations": 31, "People": 25},
    "locations": ["Bengaluru", "Mumbai", "Remote India"]
  },
  "employees": [
    {"employee_id": "EMP-1042", "name": "Maya Patel", "preferred_name": "Maya", "title": "Product Designer", "department": "Product & Design", "manager_id": "EMP-1007", "location": "Bengaluru", "work_email": "maya.patel@people.demo", "extension": "2142", "phone": "+91 90000 01042"},
    {"employee_id": "EMP-1007", "name": "Jordan Lee", "preferred_name": "Jordan", "title": "Director of Product Design", "department": "Product & Design", "manager_id": "EMP-0901", "location": "Bengaluru", "work_email": "jordan.lee@people.demo", "extension": "2107", "phone": "+91 90000 01007"},
    {"employee_id": "HR-2001", "name": "Priya Sharma", "preferred_name": "Priya", "title": "HR Operations Manager", "department": "People", "manager_id": "HR-2000", "location": "Bengaluru", "work_email": "priya.sharma@people.demo", "extension": "2201", "phone": "+91 90000 02001"}
  ],
  "leave_balances": {"EMP-1042": {"vacation": 12, "sick": 7, "personal": 3}},
  "payslips": {"EMP-1042": {"period": "July 2026", "pay_date": "2026-07-31", "currency": "INR", "gross_pay": 180000, "deductions": 30000, "net_pay": 150000, "status": "Paid"}},
  "holidays": [{"date": "2026-08-15", "name": "Independence Day", "locations": ["Bengaluru", "Mumbai", "Remote India"]}],
  "calendar_events": {"EMP-1042": [{"id": "EVT-1408", "title": "Design Weekly Sync", "starts_at": "2026-08-14T10:00:00+05:30", "duration_minutes": 45, "location": "Product Studio", "description": "The Product & Design team reviews current work, design decisions, blockers, and next-week priorities."}]},
  "tasks": {"EMP-1042": [{"id": "TASK-31", "title": "Prepare checkout usability review", "priority": "high", "due_date": "2026-08-14", "status": "in_progress"}]},
  "hr_contacts": [{"employee_id": "HR-2001", "area": "HR operations"}, {"employee_id": "HR-2002", "name": "Arun Mehta", "work_email": "arun.mehta@people.demo", "extension": "2202", "area": "Benefits and payroll"}],
  "learning_programs": [{"id": "LP-12", "name": "Creative Facilitation Lab", "starts_on": "2026-09-04", "format": "Workshop", "eligibility": "All employees", "seats_available": 8}],
  "policies": [{"id": "POL-REMOTE", "title": "Hybrid & Remote Work", "keywords": ["remote", "hybrid", "home"], "summary": "Employees may work remotely up to three days per week with manager approval. Tuesday and Thursday are collaboration days."}]
}
```

Add these exact additional fixture records:

- Directory: `EMP-1031` Rohan Iyer (Senior Engineer), `EMP-1088` Aisha Khan (Product Manager), `EMP-1124` Neha Rao (Sales Manager), `EMP-1150` Vikram Das (Operations Analyst), and `HR-2002` Arun Mehta (Benefits Specialist).
- Holidays: Gandhi Jayanti on `2026-10-02`, Diwali on `2026-11-08`, and Christmas Day on `2026-12-25`.
- Maya's tasks: `TASK-32` Update design-system empty states, `TASK-33` Review research synthesis, and `TASK-34` Submit learning plan.
- Learning: `LP-13` Advanced Figma Systems and `LP-14` New Manager Foundations.
- Policies: `POL-TIME-OFF`, `POL-CONDUCT`, `POL-LEARNING`, and `POL-PAYROLL`, each with keywords and a complete two-sentence summary.

Every record must use `.demo` email addresses or the fictional `+91 90000` phone range.

- [ ] **Step 4: Implement fixture loading and date normalization**

```python
class FixtureRepository:
    def __init__(self, path: Path | None = None) -> None:
        fixture_path = path or Path(__file__).parents[2] / "data" / "hrms-fixtures.json"
        self._data = json.loads(fixture_path.read_text(encoding="utf-8"))

    def employee(self, employee_id: str) -> dict[str, Any]:
        return next(item for item in self._data["employees"] if item["employee_id"] == employee_id)
```

```python
def resolve_date_input(value: str, today: date) -> date:
    if re.fullmatch(r"\d{2}-\d{2}", value):
        month, day = map(int, value.split("-"))
        candidate = date(today.year, month, day)
        return candidate if candidate > today else date(today.year + 1, month, day)
    candidate = date.fromisoformat(value)
    if candidate <= today:
        raise DateResolutionError("The explicitly dated leave request is in the past.")
    return candidate
```

Convert missing records and invalid calendar dates into `FixtureNotFoundError` and `DateResolutionError` with safe messages.

- [ ] **Step 5: Run the focused and complete Python test suites**

```bash
PYTHONPATH=agent .venv/bin/python -m unittest agent.tests.test_fixtures agent.tests.test_dates -v
npm run test:agent
```

Expected: focused tests and all existing Python tests pass.

- [ ] **Step 6: Commit the grounded data layer**

```bash
git add data/hrms-fixtures.json agent/hr_voice_agent/fixtures.py agent/hr_voice_agent/dates.py agent/tests/test_fixtures.py agent/tests/test_dates.py
git commit -m "feat: add grounded HRMS demo fixtures"
```

---

### Task 3: Add a Process-Safe SQLite Action Store

**Files:**
- Create: `agent/hr_voice_agent/action_store.py`
- Create: `agent/tests/test_action_store.py`
- Modify: `.env.example`

**Interfaces:**
- Consumes: actor IDs and fixture entity IDs from Task 2.
- Produces: `ActionStore`, `PendingAction`, `LeaveRequest`, `prepare_action`, `execute_action`, `list_leave_requests`, and `get_profile_overrides`.

- [ ] **Step 1: Write failing persistence, expiry, and cross-instance tests**

```python
class ActionStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "demo.sqlite"
        self.store = ActionStore(self.path, now=lambda: datetime(2026, 8, 13, tzinfo=timezone.utc))

    def test_leave_request_is_visible_to_another_store_instance(self):
        created = self.store.create_leave_request("EMP-1042", "2026-08-14", "2026-08-20", "vacation", 7)
        second = ActionStore(self.path)
        self.assertEqual(second.list_leave_requests(status="pending_hr")[0].id, created.id)

    def test_confirmation_is_actor_scoped_single_use_and_expiring(self):
        pending = self.store.prepare_action(actor_id="EMP-1042", action_type="profile_update", payload={"preferred_name": "Maya Joshi"}, prompt="Confirm name update?")
        with self.assertRaises(ActionAuthorizationError):
            self.store.confirm_action(pending.id, actor_id="HR-2001")
        self.store.execute_action(pending.id, actor_id="EMP-1042")
        with self.assertRaises(ActionStateError):
            self.store.execute_action(pending.id, actor_id="EMP-1042")
```

- [ ] **Step 2: Run the store tests and verify the missing-module failure**

```bash
PYTHONPATH=agent .venv/bin/python -m unittest agent.tests.test_action_store -v
```

Expected: FAIL because `action_store` does not exist.

- [ ] **Step 3: Implement schema initialization and transaction boundaries**

Create tables with these fields:

```sql
CREATE TABLE IF NOT EXISTS pending_actions (
  id TEXT PRIMARY KEY,
  actor_id TEXT NOT NULL,
  action_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  prompt TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  consumed_at TEXT
);
CREATE TABLE IF NOT EXISTS leave_requests (
  id TEXT PRIMARY KEY,
  employee_id TEXT NOT NULL,
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,
  leave_type TEXT NOT NULL,
  days INTEGER NOT NULL,
  status TEXT NOT NULL,
  decided_by TEXT,
  decision_note TEXT,
  created_at TEXT NOT NULL,
  decided_at TEXT
);
CREATE TABLE IF NOT EXISTS profile_overrides (
  employee_id TEXT NOT NULL,
  field TEXT NOT NULL,
  value TEXT NOT NULL,
  updated_by TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (employee_id, field)
);
```

Use `sqlite3.connect(self._path, timeout=5)`, `PRAGMA journal_mode=WAL`, parameterized statements, and `with connection:` transactions. The default path is `Path(os.getenv("HRMS_DEMO_DB", "agent/data/hrms-demo.sqlite"))`.

- [ ] **Step 4: Implement actor-scoped confirmation and domain writes**

`execute_action` must start one `BEGIN IMMEDIATE` transaction, select a row matching `id`, `actor_id`, `consumed_at IS NULL`, and `expires_at > now`, apply the whitelisted action payload to `leave_requests` or `profile_overrides`, and mark the action consumed before committing. If the row is unusable, distinguish not-found, wrong actor, expired, and already-consumed with safe typed errors. Roll back both consumption and the write when either operation fails.

- [ ] **Step 5: Add safe environment configuration**

Add to `.env.example`:

```env
# Optional local mutable demo state.
HRMS_DEMO_DB=agent/data/hrms-demo.sqlite
DEMO_SESSION_SECRET=replace-with-at-least-32-random-characters
```

- [ ] **Step 6: Run tests and commit**

```bash
PYTHONPATH=agent .venv/bin/python -m unittest agent.tests.test_action_store -v
npm run test:agent
git add .env.example agent/hr_voice_agent/action_store.py agent/tests/test_action_store.py
git commit -m "feat: persist simulated HRMS actions"
```

Expected: all Python tests pass and no SQLite file is staged.

---

### Task 4: Build Role-Enforced HRMS Domain Services

**Files:**
- Create: `agent/hr_voice_agent/access.py`
- Replace: `agent/hr_voice_agent/hrms.py`
- Replace: `agent/hr_voice_agent/domain_adapter.py`
- Modify: `agent/tests/test_hrms.py`
- Modify: `agent/tests/test_domain_adapter.py`

**Interfaces:**
- Consumes: `FixtureRepository`, `resolve_date_input`, and `ActionStore` from Tasks 2–3.
- Produces: `Actor(user_id: str, role: Role)`, `Role.EMPLOYEE`, `Role.HR_ADMIN`, `EmployeeDomainAdapter`, `HRAdminDomainAdapter`, and structured `ToolResult` dictionaries.

- [ ] **Step 1: Replace narrow service tests with failing role and expanded-data tests**

```python
def test_employee_gets_grounded_conversation_gap_answers(self):
    self.assertEqual(self.employee.get_company_overview()["headcount"], 248)
    self.assertEqual(self.employee.get_manager_contact()["work_email"], "jordan.lee@people.demo")
    self.assertEqual(self.employee.get_calendar_event("weekly sync")["id"], "EVT-1408")
    self.assertEqual(self.employee.get_latest_payslip()["net_pay"], 150000)

def test_employee_cannot_use_hr_directory_or_decisions(self):
    with self.assertRaises(PermissionDeniedError):
        self.service.list_pending_leave_requests(self.employee_actor)

def test_leave_date_without_year_uses_next_future_occurrence(self):
    result = self.employee.prepare_leave_request("08-14", "08-20", "vacation")
    self.assertEqual(result["start_date"], "2026-08-14")
    self.assertEqual(result["end_date"], "2026-08-20")

def test_domain_validation_returns_actionable_result_not_exception(self):
    result = self.employee.prepare_leave_request("2025-08-14", "2025-08-20", "vacation")
    self.assertEqual(result["status"], "invalid")
    self.assertIn("past", result["message"])

def test_reports_current_bengaluru_time(self):
    result = self.employee.get_current_local_time()
    self.assertEqual(result["timezone"], "Asia/Kolkata")
    self.assertEqual(result["date"], "2026-08-13")
```

- [ ] **Step 2: Run the focused tests and confirm failures**

```bash
PYTHONPATH=agent .venv/bin/python -m unittest agent.tests.test_hrms agent.tests.test_domain_adapter -v
```

Expected: FAIL because role actors and expanded methods do not exist.

- [ ] **Step 3: Implement explicit actor authorization**

```python
class Role(str, Enum):
    EMPLOYEE = "employee"
    HR_ADMIN = "hr_admin"

@dataclass(frozen=True)
class Actor:
    user_id: str
    role: Role

def require_role(actor: Actor, *allowed: Role) -> None:
    if actor.role not in allowed:
        raise PermissionDeniedError("This operation is not available for your role.")
```

Every service method accepts `actor`. Employee-specific reads use `actor.user_id`; they do not accept an arbitrary employee ID.

- [ ] **Step 4: Implement role-specific adapters and structured errors**

Employee adapter methods:

```python
get_my_profile()
get_leave_balance()
get_latest_payslip()
get_company_overview()
get_manager_contact()
get_hr_contacts()
get_calendar_event(query: str)
get_holiday_calendar()
get_current_local_time()
get_tasks()
prioritize_tasks()
search_hr_knowledge(query: str)
prepare_leave_request(start_date: str, end_date: str, leave_type: str)
prepare_profile_update(field: str, value: str)
execute_pending_action(pending_id: str, confirmed: bool)
cancel_pending_action(pending_id: str)
```

HR adapter methods:

```python
get_company_overview()
search_employee_directory(query: str)
get_employee_work_profile(employee_id: str)
get_hr_contacts()
list_pending_leave_requests()
prepare_leave_decision(request_id: str, decision: str, note: str)
prepare_employee_profile_update(employee_id: str, field: str, value: str)
search_hr_knowledge(query: str)
get_current_local_time()
execute_pending_action(pending_id: str, confirmed: bool)
cancel_pending_action(pending_id: str)
```

Allowed employee profile fields are `preferred_name`, `phone`, and `location`. HR may additionally update `title`, `department`, and `manager_id`. Reject every other field before preparing an action.

- [ ] **Step 5: Test cross-session request and approval**

```python
prepared = employee.prepare_leave_request("08-14", "08-20", "vacation")
submitted = employee.execute_pending_action(prepared["pending_id"], confirmed=True)
queue = hr.list_pending_leave_requests()
self.assertEqual(queue[0]["request_id"], submitted["request_id"])
decision = hr.prepare_leave_decision(submitted["request_id"], "approved", "Coverage confirmed")
approved = hr.execute_pending_action(decision["pending_id"], confirmed=True)
self.assertEqual(approved["status"], "approved")
```

- [ ] **Step 6: Run all Python tests and commit**

```bash
npm run test:agent
git add agent/hr_voice_agent/access.py agent/hr_voice_agent/hrms.py agent/hr_voice_agent/domain_adapter.py agent/tests/test_hrms.py agent/tests/test_domain_adapter.py
git commit -m "feat: enforce employee and HR domain permissions"
```

Expected: all Python tests pass.

---

### Task 5: Create Role-Specific Voice Agents and Reliable Turn Handling

**Files:**
- Replace: `agent/hr_voice_agent/voice_agent.py`
- Modify: `agent/agent.py`
- Modify: `agent/tests/test_voice_agent.py`
- Create: `agent/tests/test_agent_entrypoint.py`

**Interfaces:**
- Consumes: `Actor`, `EmployeeDomainAdapter`, and `HRAdminDomainAdapter` from Task 4.
- Produces: `create_voice_agent(actor, fixtures, store, now) -> Agent`, `EmployeeVoiceAgent`, `HRAdminVoiceAgent`, exact confirmation guards, and trusted participant-to-actor resolution.

- [ ] **Step 1: Write failing agent factory and tool-boundary tests**

```python
def test_employee_and_hr_agents_register_different_tools(self):
    employee = create_voice_agent(Actor("EMP-1042", Role.EMPLOYEE), self.fixtures, self.store, self.now)
    hr = create_voice_agent(Actor("HR-2001", Role.HR_ADMIN), self.fixtures, self.store, self.now)
    self.assertIn("get_latest_payslip", {tool.id for tool in employee.tools})
    self.assertNotIn("search_employee_directory", {tool.id for tool in employee.tools})
    self.assertIn("search_employee_directory", {tool.id for tool in hr.tools})
    self.assertNotIn("get_latest_payslip", {tool.id for tool in hr.tools})

def test_instructions_include_current_date_timezone_and_role(self):
    agent = create_voice_agent(
        Actor("EMP-1042", Role.EMPLOYEE),
        self.fixtures,
        self.store,
        now=lambda: datetime(2026, 8, 13, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
    )
    self.assertIn("2026-08-13", agent.instructions)
    self.assertIn("Asia/Kolkata", agent.instructions)

def test_nickname_is_session_scoped(self):
    first = create_voice_agent(Actor("EMP-1042", Role.EMPLOYEE), self.fixtures, self.store, self.now)
    second = create_voice_agent(Actor("EMP-1042", Role.EMPLOYEE), self.fixtures, self.store, self.now)
    self.assertEqual(first.remember_nickname("Jay")["nickname"], "Jay")
    self.assertIsNone(second.nickname)
```

- [ ] **Step 2: Run agent tests and verify they fail**

```bash
PYTHONPATH=agent .venv/bin/python -m unittest agent.tests.test_voice_agent agent.tests.test_agent_entrypoint -v
```

Expected: FAIL because the role-specific agent factory is absent.

- [ ] **Step 3: Implement separate tool classes with shared behavior**

Keep shared confirmation and nickname helpers in a small base class, including `remember_nickname(name: str) -> dict[str, str]`. The decorated `set_assistant_nickname` tool delegates to that helper. Decorate only role-appropriate domain methods on each concrete agent. `execute_pending_action` must compute confirmation from the exact prompt returned by the adapter and the final two chat messages; it must never accept a model-provided `confirmed` argument.

The base instructions must include:

```text
Today is 2026-08-13 in Asia/Kolkata. If the user omits a year, pass dates to tools as MM-DD. If the user states a year, pass YYYY-MM-DD exactly. Never invent a year.
Use tools for every company or employee fact. Describe tool validation messages directly and do not call them technical errors.
You may accept and use a harmless assistant nickname for this session.
```

- [ ] **Step 4: Resolve the actor from trusted LiveKit participant attributes**

```python
participant = await ctx.wait_for_participant()
role_value = participant.attributes.get("hrms.role")
user_id = participant.attributes.get("hrms.user_id")
if user_id != participant.identity or role_value not in {"employee", "hr_admin"}:
    raise RuntimeError("Trusted HRMS participant attributes are missing or invalid.")
actor = Actor(user_id=user_id, role=Role(role_value))
```

Do this before starting `AgentSession`.

- [ ] **Step 5: Tune turn handling based on the observed fragmented transcript**

```python
turn_handling=TurnHandlingOptions(
    turn_detection=inference.TurnDetector(),
    endpointing={"min_delay": 0.8, "max_delay": 3.0},
    interruption={
        "enabled": True,
        "mode": "adaptive",
        "min_duration": 0.8,
        "min_words": 2,
        "resume_false_interruption": True,
        "false_interruption_timeout": 2.0,
    },
)
```

Add an entrypoint test that imports `agent.py`, inspects a factored `build_turn_handling()` result, and asserts these exact values.

- [ ] **Step 6: Run Python tests and the CLI smoke test**

```bash
npm run test:agent
PYTHONPATH=agent .venv/bin/python agent/agent.py --help
```

Expected: all Python tests pass and the CLI exposes `start`, `dev`, and `console`.

- [ ] **Step 7: Commit the role-specific agents**

```bash
git add agent/agent.py agent/hr_voice_agent/voice_agent.py agent/tests/test_voice_agent.py agent/tests/test_agent_entrypoint.py
git commit -m "feat: add role-aware HR voice agents"
```

---

### Task 6: Add Signed Demo Authentication and Trusted LiveKit Tokens

**Files:**
- Modify: `package.json`
- Modify: `package-lock.json`
- Create: `web/lib/demo-users.ts`
- Create: `web/lib/session-token.ts`
- Create: `web/lib/server-session.ts`
- Create: `app/api/auth/login/route.ts`
- Create: `app/api/auth/logout/route.ts`
- Modify: `app/api/token/route.ts`
- Create: `web/test/demo-auth.test.ts`
- Modify: `web/test/token-route.test.ts`

**Interfaces:**
- Consumes: fixed credentials and the role names `employee` and `hr_admin`.
- Produces: `DemoSession`, `authenticateDemoUser`, `signDemoSession`, `verifyDemoSession`, `readDemoSession`, login/logout endpoints, and role-bearing LiveKit tokens.

- [ ] **Step 1: Read the installed Next.js 16 references completely**

Read:

```bash
sed -n '1,260p' node_modules/next/dist/docs/01-app/02-guides/authentication.md
sed -n '1,240p' node_modules/next/dist/docs/01-app/03-api-reference/04-functions/cookies.md
sed -n '1,220p' node_modules/next/dist/docs/01-app/01-getting-started/15-route-handlers.md
```

Use asynchronous `cookies()` and Node route handlers exactly as documented.

- [ ] **Step 2: Install the direct JWT dependency**

```bash
npm install jose@latest
```

Expected: `jose` appears under direct dependencies.

- [ ] **Step 3: Write failing pure auth tests**

```typescript
it("authenticates only the two exact demo accounts", () => {
  expect(authenticateDemoUser("maya@people.demo", "employee123")).toMatchObject({
    userId: "EMP-1042",
    role: "employee",
  });
  expect(authenticateDemoUser("priya@people.demo", "hradmin123")).toMatchObject({
    userId: "HR-2001",
    role: "hr_admin",
  });
  expect(authenticateDemoUser("maya@people.demo", "wrong")).toBeNull();
});

it("rejects a modified signed session", async () => {
  const token = await signDemoSession(employeeSession, TEST_SECRET);
  await expect(verifyDemoSession(`${token}x`, TEST_SECRET)).resolves.toBeNull();
});
```

- [ ] **Step 4: Run auth tests and verify missing exports**

```bash
npm test -- web/test/demo-auth.test.ts
```

Expected: FAIL because auth modules do not exist.

- [ ] **Step 5: Implement demo users and signed sessions**

```typescript
export type DemoRole = "employee" | "hr_admin";
export type DemoSession = { userId: string; role: DemoRole; name: string; email: string };

const DEMO_USERS = [
  { email: "maya@people.demo", password: "employee123", userId: "EMP-1042", role: "employee", name: "Maya Patel" },
  { email: "priya@people.demo", password: "hradmin123", userId: "HR-2001", role: "hr_admin", name: "Priya Sharma" },
] as const;
```

Use `SignJWT` and `jwtVerify` with HS256, a 12-hour expiry, issuer `people-demo`, and audience `hrms-voice-demo`. `server-session.ts` reads `people_demo_session` from `await cookies()`. `getSessionSecret()` requires `DEMO_SESSION_SECRET` to be at least 32 characters in production and uses the fixed local-only fallback `people-demo-local-session-secret-2026` in development and tests.

- [ ] **Step 6: Implement login/logout route tests and endpoints**

Login accepts JSON `{ email, password }`, returns 204, and sets an HTTP-only, same-site `lax`, path `/` cookie. Invalid credentials return 401 with `{ error: "Invalid demo credentials" }`. Logout returns 204 and expires the cookie.

```typescript
const session = authenticateDemoUser(email, password);
if (!session) {
  return NextResponse.json({ error: "Invalid demo credentials" }, { status: 401 });
}
const response = new NextResponse(null, { status: 204 });
response.cookies.set("people_demo_session", await signDemoSession(session), {
  httpOnly: true,
  sameSite: "lax",
  secure: process.env.NODE_ENV === "production",
  path: "/",
  maxAge: 60 * 60 * 12,
});
return response;
```

- [ ] **Step 7: Require the session when minting a LiveKit token**

Update the token test to sign an employee and HR cookie. Assert:

```typescript
expect(employeeClaims.sub).toBe("EMP-1042");
expect(employeeClaims.attributes).toMatchObject({
  "hrms.user_id": "EMP-1042",
  "hrms.role": "employee",
});
expect(hrClaims.attributes["hrms.role"]).toBe("hr_admin");
expect(unauthenticatedResponse.status).toBe(401);
```

The endpoint must continue server-generating the room, using `VOICE_AGENT_NAME`, and granting microphone-only publishing.

- [ ] **Step 8: Run web tests and commit**

```bash
npm test -- web/test/demo-auth.test.ts web/test/token-route.test.ts
npm run typecheck
git add package.json package-lock.json web/lib/demo-users.ts web/lib/session-token.ts web/lib/server-session.ts app/api/auth/login/route.ts app/api/auth/logout/route.ts app/api/token/route.ts web/test/demo-auth.test.ts web/test/token-route.test.ts
git commit -m "feat: add role-aware demo authentication"
```

---

### Task 7: Build Login and Role-Adaptive Dashboards

**Files:**
- Create: `app/login/page.tsx`
- Create: `web/components/login-form.tsx`
- Create: `web/components/role-dashboard.tsx`
- Create: `web/components/hr-admin-dashboard.tsx`
- Modify: `web/components/hr-dashboard.tsx`
- Modify: `web/components/voice-assistant.tsx`
- Modify: `web/components/assistant-panel.tsx`
- Modify: `app/page.tsx`
- Modify: `app/globals.css`
- Create: `web/test/login-form.test.tsx`
- Create: `web/test/role-dashboard.test.tsx`
- Modify: `web/test/hr-dashboard.test.tsx`

**Interfaces:**
- Consumes: `DemoSession` and auth endpoints from Task 6; existing `VoiceAssistantConfig` and `AssistantPanelCopy`.
- Produces: a login screen, logout control, `RoleDashboard({ session })`, and role-specific voice panel copy without duplicating LiveKit session code.

- [ ] **Step 1: Write failing login behavior tests**

```typescript
it("submits selected demo credentials and refreshes after success", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));
  render(<LoginForm />);
  await user.click(screen.getByRole("button", { name: "Continue as employee" }));
  expect(fetch).toHaveBeenCalledWith("/api/auth/login", expect.objectContaining({ method: "POST" }));
});

it("shows a safe invalid-credential error", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
  render(<LoginForm />);
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Check the demo email and password");
});
```

- [ ] **Step 2: Write failing role-dashboard tests**

```typescript
it("renders employee content and prompts", () => {
  render(<RoleDashboard session={employeeSession} />);
  expect(screen.getByText("12 days")).toBeInTheDocument();
  expect(screen.getByText("Explain Design Weekly Sync")).toBeInTheDocument();
  expect(screen.queryByText("Leave approvals")).not.toBeInTheDocument();
});

it("renders HR workforce and approval content", () => {
  render(<RoleDashboard session={hrSession} />);
  expect(screen.getByText("248")).toBeInTheDocument();
  expect(screen.getByText("Leave approvals")).toBeInTheDocument();
  expect(screen.getByText("Show pending leave requests")).toBeInTheDocument();
});
```

- [ ] **Step 3: Run UI tests and confirm failures**

```bash
npm test -- web/test/login-form.test.tsx web/test/role-dashboard.test.tsx
```

Expected: FAIL because the components do not exist.

- [ ] **Step 4: Implement the demo login page**

Show both account cards, prefill the selected account, allow manual entry, label the experience “Fictional HRMS demo,” and redirect to `/` using `window.location.assign("/")` after success. Do not place LiveKit credentials anywhere in client code.

```tsx
<button onClick={() => selectAccount("employee")} type="button">Continue as employee</button>
<button onClick={() => selectAccount("hr_admin")} type="button">Continue as HR Admin</button>
<form onSubmit={submitLogin}>
  <label>Email<input name="email" type="email" value={email} onChange={onEmailChange} /></label>
  <label>Password<input name="password" type="password" value={password} onChange={onPasswordChange} /></label>
  <button disabled={submitting} type="submit">Sign in</button>
</form>
```

- [ ] **Step 5: Make the home page session-aware**

```typescript
export default async function HomePage() {
  const session = await readDemoSession();
  if (!session) redirect("/login");
  return <RoleDashboard session={session} />;
}
```

Create role-specific `AssistantPanelCopy` objects at the composition boundary. Employee suggestions include leave balance, weekly sync, holiday, and payslip. HR suggestions include workforce summary, directory search, and pending leave approvals.

- [ ] **Step 6: Implement the selected role-adaptive layout**

Reuse the sidebar, topbar, assistant column, typography, responsive breakpoints, and voice controls. Employee mode keeps existing cards plus tasks and learning. HR mode replaces personal cards with headcount, on-leave, pending approvals, directory, and HR contacts. Add a visible role badge and logout button.

```tsx
export function RoleDashboard({ session }: { session: DemoSession }) {
  const assistant = <VoiceAssistant config={voiceConfigFor(session.role)} />;
  return session.role === "hr_admin"
    ? <HRAdminDashboard assistant={assistant} session={session} />
    : <HRDashboard assistant={assistant} session={session} />;
}
```

- [ ] **Step 7: Run UI, web, and type checks**

```bash
npm test -- web/test/login-form.test.tsx web/test/role-dashboard.test.tsx web/test/hr-dashboard.test.tsx web/test/assistant-panel.test.tsx
npm test
npm run typecheck
```

Expected: all web tests pass.

- [ ] **Step 8: Commit role-adaptive UI**

```bash
git add app/login/page.tsx app/page.tsx app/globals.css web/components/login-form.tsx web/components/role-dashboard.tsx web/components/hr-admin-dashboard.tsx web/components/hr-dashboard.tsx web/components/voice-assistant.tsx web/components/assistant-panel.tsx web/test/login-form.test.tsx web/test/role-dashboard.test.tsx web/test/hr-dashboard.test.tsx
git commit -m "feat: add employee and HR demo experiences"
```

---

### Task 8: Verify the Full Role-Aware Voice Flow

**Files:**
- Modify if a verified defect requires it: files from Tasks 2–7 only
- Test: all `web/test/*.test.*` and `agent/tests/test_*.py`

**Interfaces:**
- Consumes: the complete role-aware application.
- Produces: evidence that authentication, tool authorization, expanded data, confirmed actions, UI, and production build work together.

- [ ] **Step 1: Reset mutable demo state**

Stop the worker. Move `agent/data/hrms-demo.sqlite` to a timestamped backup if it exists; do not delete it destructively. Restart the worker so schema initialization creates a clean store.

- [ ] **Step 2: Run all automated verification**

```bash
npm run test:all
npm run typecheck
.venv/bin/python -m compileall -q agent
npm run build
git diff --check
```

Expected: every test passes, compilation and build exit 0, and no whitespace errors exist.

- [ ] **Step 3: Run authentication and token smoke checks**

Start `npm run dev`. Use `curl` with a cookie jar to log in as Maya, call `/api/token`, decode only the JWT payload, and confirm `hrms.role=employee`. Repeat with Priya and confirm `hrms.role=hr_admin`. Never print or store LiveKit secrets.

- [ ] **Step 4: Run the manual employee voice scenario**

Log in as Maya and verify audible, grounded answers for:

```text
Call yourself Jay for this conversation.
What is Design Weekly Sync?
Is Independence Day the next holiday?
What was my July net pay?
Who is my manager and what is their work email?
Prioritize my tasks.
Request vacation from August 14 through August 20.
Yes, submit it.
```

Expected: Jay is used in-session; fixture answers are returned; the date resolves to 2026; the exact confirmation prompt is spoken; a simulated request ID is returned.

- [ ] **Step 5: Run the manual HR voice scenario**

Log out, log in as Priya, and verify:

```text
How many employees work here?
Find Maya Patel.
Show pending leave requests.
Approve Maya's request with the note Coverage confirmed.
Yes, approve it.
```

Expected: the employee request appears across sessions; the exact approval confirmation is required; the request becomes approved with an audit ID.

- [ ] **Step 6: Verify permission denial and session cleanup**

As Maya, attempt “Show all pending leave requests” and verify a capability explanation with no data. Log out while voice is connected and verify the room ends and `/api/token` returns 401 afterward.

- [ ] **Step 7: Final source review and commit verified fixes only**

Inspect:

```bash
git status --short
git diff --stat
git diff
```

If verification required changes, rerun the affected failing test, the complete suite, and build before committing:

```bash
git add data app web agent .env.example .gitignore package.json package-lock.json tsconfig.json vitest.config.ts
git commit -m "fix: complete role-aware HRMS voice flow"
```

Do not commit `.env.local`, `.superpowers`, SQLite runtime files, logs, tokens, or recordings.
