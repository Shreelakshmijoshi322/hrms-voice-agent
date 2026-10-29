"""Server-side bridge from the LiveKit voice agent to the real HRMS AI service.

The browser never sends an HRMS bearer token into the room.  The token endpoint
places an encrypted copy of the HttpOnly HRMS session cookie in signed LiveKit
participant metadata. This module decrypts that value inside the trusted voice
worker and forwards it to the same AI WebSocket used by the HRMS UI. The AI
service performs the cookie-to-AI-token exchange with Core itself.
"""

from __future__ import annotations

import asyncio
import base64
import difflib
import hashlib
import json
import os
import re
import uuid
from datetime import datetime
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from websockets.sync.client import connect


class HRMSBackendError(RuntimeError):
    """The voice worker could not complete an HRMS AI request."""


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def decrypt_session_cookie(encrypted: str, livekit_api_secret: str) -> str:
    """Decrypt the v1 cookie envelope produced by the Next token endpoint."""
    try:
        version, iv_raw, tag_raw, ciphertext_raw = encrypted.split(".", 3)
        if version != "v1":
            raise ValueError("unsupported cookie envelope")
        iv = _b64decode(iv_raw)
        tag = _b64decode(tag_raw)
        ciphertext = _b64decode(ciphertext_raw)
        key = hashlib.sha256(
            f"{livekit_api_secret}:hrms-session-cookie".encode("utf-8")
        ).digest()

        # AES-GCM is available in the Python standard library only through
        # cryptography, so defer the import until the HRMS bridge is enabled.
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        plaintext = AESGCM(key).decrypt(iv, ciphertext + tag, None)
        return plaintext.decode("utf-8")
    except Exception as exc:  # do not leak ciphertext or key material
        raise HRMSBackendError("voice session cookie could not be decrypted") from exc


@dataclass(frozen=True)
class HRMSBackendConfig:
    ai_ws_url: str
    core_session_token_url: str
    core_session_token_secret: str
    core_api_url: str
    livekit_api_secret: str
    timezone: str = "Asia/Kolkata"

    @classmethod
    def from_environment(cls) -> "HRMSBackendConfig":
        return cls(
            ai_ws_url=os.getenv("HRMS_AI_WS_URL", "ws://localhost:8083/api/v1/chat/widget"),
            core_session_token_url=os.getenv(
                "CORE_SESSION_TOKEN_URL",
                "http://localhost:8081/internal/ai/session-token",
            ),
            core_session_token_secret=os.getenv("CORE_SESSION_TOKEN_SECRET", ""),
            core_api_url=os.getenv("HRMS_CORE_URL", "http://localhost:8081"),
            livekit_api_secret=os.getenv("LIVEKIT_API_SECRET", ""),
            timezone=os.getenv("APP_TIMEZONE", "Asia/Kolkata"),
        )


class HRMSBackend:
    def __init__(self, config: HRMSBackendConfig):
        self.config = config

    async def ask(self, encrypted_cookie: str, query: str) -> str:
        return await asyncio.to_thread(self._ask_sync, encrypted_cookie, query)

    async def ask_departments(self, encrypted_cookie: str) -> str:
        """Read departments directly from Core when the LLM is unavailable."""
        return await asyncio.to_thread(self._ask_departments_sync, encrypted_cookie)

    async def ask_employee_search(self, encrypted_cookie: str, query: str) -> str:
        """Resolve an employee code/name directly from Core.

        Employee lookup is deterministic reference data. Keeping this path out
        of the LLM prevents provider overloads or model guesses from producing
        a fabricated employee, especially for speech-recognised codes such as
        ``e m p zero zero zero zero one one``.
        """
        return await asyncio.to_thread(self._ask_employee_search_sync, encrypted_cookie, query)

    async def ask_policy(self, encrypted_cookie: str, query: str) -> str:
        return await asyncio.to_thread(self._ask_policy_sync, encrypted_cookie, query)

    async def ask_leave_balance(
        self,
        encrypted_cookie: str,
        query: str,
        reference_query: str = "",
    ) -> str:
        return await asyncio.to_thread(
            self._ask_leave_balance_sync,
            encrypted_cookie,
            query,
            reference_query,
        )

    async def ask_manager_count(self, encrypted_cookie: str) -> str:
        return await asyncio.to_thread(self._ask_manager_count_sync, encrypted_cookie)

    async def ask_salary(
        self,
        encrypted_cookie: str,
        query: str,
        reference_query: str = "",
    ) -> str:
        return await asyncio.to_thread(
            self._ask_salary_sync,
            encrypted_cookie,
            query,
            reference_query,
        )

    async def ask_pending_leave_requests(self, encrypted_cookie: str, query: str) -> str:
        return await asyncio.to_thread(self._ask_pending_leave_requests_sync, encrypted_cookie, query)

    def _core_token(self, cookie: str) -> str:
        request = Request(
            self.config.core_session_token_url,
            headers={
                "Cookie": cookie,
                "X-HRMS-AI-Secret": self.config.core_session_token_secret,
            },
        )
        with urlopen(request, timeout=10) as response:
            body = json.loads(response.read().decode("utf-8"))
        payload = body.get("data", body) if isinstance(body, dict) else {}
        token = payload.get("core_access_token") or payload.get("access_token")
        if not token:
            raise HRMSBackendError("HRMS session token exchange returned no Core token")
        return str(token)

    def _core_json(self, path: str, cookie: str, core_token: str) -> dict:
        request = Request(
            f"{self.config.core_api_url.rstrip('/')}{path}",
            headers={"Authorization": f"Bearer {core_token}", "Cookie": cookie},
        )
        with urlopen(request, timeout=10) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body if isinstance(body, dict) else {"data": body}

    def _all_employees(self, cookie: str, core_token: str) -> list[dict[str, object]]:
        """Fetch the complete directory instead of relying on Core's first page."""
        page = 1
        page_size = 100
        rows: list[dict[str, object]] = []
        while True:
            body = self._core_json(
                "/api/v1/employees?" + urlencode({"page": page, "page_size": page_size}),
                cookie,
                core_token,
            )
            batch = body.get("data", body)
            if not isinstance(batch, list):
                raise HRMSBackendError("Core returned an invalid employee list")
            rows.extend(row for row in batch if isinstance(row, dict))
            meta = body.get("meta", {})
            total = int(meta.get("total", 0) or 0) if isinstance(meta, dict) else 0
            if not batch or (total and len(rows) >= total) or len(batch) < page_size:
                return rows
            page += 1

    @staticmethod
    def _employee_label(employee: dict[str, object]) -> str:
        name = " ".join(
            str(employee.get(key) or "").strip()
            for key in ("first_name", "last_name")
        ).strip() or "Unnamed employee"
        code = str(employee.get("employee_code") or "unknown code")
        return f"{name} ({code})"

    @staticmethod
    def _directory_intent(query: str) -> str | None:
        lowered = query.casefold()
        if "under admin" in lowered or "working under admin" in lowered or "report to admin" in lowered:
            return "admin_reports"
        if "employee" not in lowered and "employees" not in lowered:
            return None
        if "unassigned" in lowered:
            return "unassigned"
        # Specific name/code searches already have a separate deterministic path.
        if any(marker in lowered for marker in ("find", "search", "locate")):
            return None
        if (
            any(marker in lowered for marker in ("list", "all", "names", "employee ids", "employee id"))
            and any(marker in lowered for marker in ("employee", "employees", "names"))
        ):
            return "all"
        return None

    def _directory_answer_sync(self, encrypted_cookie: str, query: str) -> str:
        cookie = decrypt_session_cookie(encrypted_cookie, self.config.livekit_api_secret)
        core_token = self._core_token(cookie)
        employees = self._all_employees(cookie, core_token)
        intent = self._directory_intent(query)
        if intent == "all":
            if not employees:
                return "There are no employees in the directory."
            return (
                f"There are {len(employees)} employees: "
                + "; ".join(self._employee_label(employee) for employee in employees)
                + "."
            )

        if intent == "unassigned":
            try:
                departments_body = self._core_json("/api/v1/departments", cookie, core_token)
                departments = departments_body.get("data", departments_body)
            except Exception:
                departments = []
            unassigned_ids = {
                str(row.get("id"))
                for row in departments
                if isinstance(row, dict) and str(row.get("name", "")).strip().casefold() == "unassigned"
            }
            matches = [
                employee for employee in employees
                if employee.get("department_id") in (None, "", 0)
                or str(employee.get("department_id")) in unassigned_ids
                or str(employee.get("department_name", "")).strip().casefold() == "unassigned"
            ]
            if not matches:
                return "There are no unassigned employees in the organization."
            return (
                f"There are {len(matches)} unassigned employees: "
                + "; ".join(self._employee_label(employee) for employee in matches)
                + "."
            )

        if intent == "admin_reports":
            admin_ids = {
                str(employee.get("id"))
                for employee in employees
                if "admin" in " ".join(
                    str(employee.get(key) or "")
                    for key in ("first_name", "last_name", "email", "employee_code", "designation_name")
                ).casefold()
            }
            matches = [
                employee for employee in employees
                if str(employee.get("manager_id")) in admin_ids
                or "admin" in str(employee.get("manager_name", "")).casefold()
            ]
            if not matches:
                return "I couldn't find any employees whose reporting manager is named Admin in the HRMS directory."
            return (
                f"{len(matches)} employees report to Admin: "
                + "; ".join(self._employee_label(employee) for employee in matches)
                + "."
            )

        raise HRMSBackendError("unsupported directory request")

    def _ask_departments_sync(self, encrypted_cookie: str) -> str:
        if not encrypted_cookie:
            raise HRMSBackendError("voice session is not linked to an HRMS login")
        if not self.config.livekit_api_secret:
            raise HRMSBackendError("LIVEKIT_API_SECRET is not configured for the voice worker")
        if not self.config.core_session_token_secret:
            raise HRMSBackendError("CORE_SESSION_TOKEN_SECRET is not configured for the voice worker")

        cookie = decrypt_session_cookie(encrypted_cookie, self.config.livekit_api_secret)
        try:
            core_token = self._core_token(cookie)
            departments_body = self._core_json("/api/v1/departments", cookie, core_token)
            departments = departments_body.get("data", departments_body)
            if not isinstance(departments, list):
                raise HRMSBackendError("Core returned an invalid department list")

            counts: dict[str, int] = {}
            try:
                employees_body = self._core_json(
                    "/api/v1/employees?" + urlencode({"status": "active", "page": 1, "page_size": 1000}),
                    cookie,
                    core_token,
                )
                employees = employees_body.get("data", employees_body)
                if isinstance(employees, list):
                    for employee in employees:
                        if isinstance(employee, dict) and employee.get("department_id") is not None:
                            key = str(employee["department_id"])
                            counts[key] = counts.get(key, 0) + 1
            except Exception:
                # Department reference access is still useful if directory
                # counts are not available to this caller.
                counts = {}

            if not departments:
                return "There are no departments configured in the office."
            parts: list[str] = []
            for department in departments:
                if not isinstance(department, dict):
                    continue
                name = str(department.get("name") or "Unnamed department")
                key = str(department.get("id"))
                if key in counts:
                    count = counts[key]
                    suffix = "employee" if count == 1 else "employees"
                    parts.append(f"{name} ({count} {suffix})")
                else:
                    parts.append(name)
            noun = "department" if len(parts) == 1 else "departments"
            return f"Your office has {len(parts)} {noun}: " + ", ".join(parts) + "."
        except HRMSBackendError:
            raise
        except Exception as exc:
            raise HRMSBackendError("Core department lookup failed") from exc

    @staticmethod
    def _employee_code_from_speech(query: str) -> str | None:
        digits = {
            "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
            "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
        }
        literal = re.search(r"\bemp[\s-]*([0-9][0-9\s-]{3,})", query.casefold())
        if literal:
            value = re.sub(r"[^0-9]", "", literal.group(1))
            return f"EMP-{value.zfill(6)}" if value else None

        tokens = re.findall(r"[a-z0-9]+", query.casefold())
        for index in range(len(tokens) - 2):
            if tokens[index:index + 3] != ["e", "m", "p"]:
                continue
            value: list[str] = []
            for token in tokens[index + 3:]:
                if token in digits:
                    value.append(digits[token])
                elif token.isdigit():
                    value.extend(token)
                else:
                    break
            if value:
                return f"EMP-{''.join(value).zfill(6)}"
        return None

    @staticmethod
    def _employee_search_terms(query: str) -> str:
        ignored = {
            "a", "an", "can", "find", "for", "help", "id", "me", "please",
            "search", "the", "this", "with", "employee", "employees", "person",
            "someone", "look", "locate", "tell", "about", "is", "there", "whose",
            "what", "who", "kind", "details", "detail", "give", "show", "find",
            "how", "many", "leaves", "leave", "remaining", "balance", "balances",
            "available", "days", "of", "for", "his", "her", "their", "gross",
            "salary", "salaries", "pay", "paid", "all", "list", "names", "work",
        }
        words = re.findall(r"[a-z]+", query.casefold())
        return " ".join(word for word in words if word not in ignored)

    @classmethod
    def _employee_score(cls, query: str, employee: dict[str, object]) -> float:
        name = " ".join(
            str(employee.get(key) or "")
            for key in ("first_name", "last_name")
        ).strip().casefold()
        compact_query = re.sub(r"[^a-z]", "", query.casefold())
        compact_name = re.sub(r"[^a-z]", "", name)
        if not compact_query or not compact_name:
            return 0.0
        if compact_query in compact_name or compact_name in compact_query:
            return 1.0
        return max(
            difflib.SequenceMatcher(None, compact_query, compact_name).ratio(),
            *(difflib.SequenceMatcher(None, compact_query, token).ratio()
              for token in re.findall(r"[a-z]+", name) if token),
        )

    def _ask_employee_search_sync(self, encrypted_cookie: str, query: str) -> str:
        if not encrypted_cookie:
            raise HRMSBackendError("voice session is not linked to an HRMS login")
        if not self.config.livekit_api_secret:
            raise HRMSBackendError("LIVEKIT_API_SECRET is not configured for the voice worker")
        if not self.config.core_session_token_secret:
            raise HRMSBackendError("CORE_SESSION_TOKEN_SECRET is not configured for the voice worker")

        cookie = decrypt_session_cookie(encrypted_cookie, self.config.livekit_api_secret)
        try:
            core_token = self._core_token(cookie)
            body = self._core_json(
                "/api/v1/employees?" + urlencode({"status": "active", "page": 1, "page_size": 1000}),
                cookie,
                core_token,
            )
            employees = body.get("data", body)
            if not isinstance(employees, list):
                raise HRMSBackendError("Core returned an invalid employee list")

            code = self._employee_code_from_speech(query)
            if code:
                matches = [
                    employee for employee in employees
                    if isinstance(employee, dict)
                    and str(employee.get("employee_code", "")).casefold() == code.casefold()
                ]
                search_label = code
            else:
                search_label = self._employee_search_terms(query)
                scored = [
                    (self._employee_score(search_label, employee), employee)
                    for employee in employees if isinstance(employee, dict)
                ]
                scored.sort(key=lambda item: item[0], reverse=True)
                matches = [employee for score, employee in scored[:3] if score >= 0.55]

            if not matches:
                return f'I couldn\'t find an active employee matching "{search_label}".'

            # Directory rows are enough to answer the lookup. Reference
            # metadata can be restricted for non-admin users, so treat it as
            # best-effort instead of converting a valid employee match into a
            # generic lookup failure.
            try:
                departments = self._core_json("/api/v1/departments", cookie, core_token).get("data", [])
            except Exception:
                departments = []
            try:
                designations = self._core_json("/api/v1/designations", cookie, core_token).get("data", [])
            except Exception:
                designations = []
            department_names = {str(row.get("id")): str(row.get("name", "")) for row in departments if isinstance(row, dict)}
            designation_names = {str(row.get("id")): str(row.get("name", "")) for row in designations if isinstance(row, dict)}

            descriptions: list[str] = []
            for employee in matches:
                name = " ".join(
                    str(employee.get(key) or "")
                    for key in ("first_name", "last_name")
                ).strip() or "Unnamed employee"
                employee_code = str(employee.get("employee_code") or "unknown code")
                designation = str(employee.get("designation_name") or designation_names.get(str(employee.get("designation_id")), ""))
                department = str(employee.get("department_name") or department_names.get(str(employee.get("department_id")), ""))
                status = str(employee.get("status") or "unknown")
                joined = str(employee.get("hire_date") or "unknown date")
                details = ", ".join(value for value in (designation, department, status.title(), f"Joined {joined}") if value)
                descriptions.append(f"{employee_code} — {name}" + (f" ({details})" if details else ""))

            if len(descriptions) == 1:
                return f'I found: {descriptions[0]}.'
            return f'I found {len(descriptions)} employees matching "{search_label}": ' + "; ".join(descriptions) + "."
        except HRMSBackendError:
            raise
        except Exception as exc:
            raise HRMSBackendError("Core employee lookup failed") from exc

    @staticmethod
    def _rows(body: dict) -> list[dict[str, object]]:
        rows = body.get("data", body)
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []

    def _employee_matches(
        self,
        employees: list[dict[str, object]],
        query: str,
        *,
        limit: int = 3,
    ) -> list[dict[str, object]]:
        """Match names/codes consistently for every employee-scoped read."""
        code = self._employee_code_from_speech(query)
        if code:
            return [
                employee for employee in employees
                if str(employee.get("employee_code", "")).casefold() == code.casefold()
            ][:limit]
        terms = self._employee_search_terms(query)
        if not terms:
            return []
        scored = sorted(
            ((self._employee_score(terms, employee), employee) for employee in employees),
            key=lambda item: item[0],
            reverse=True,
        )
        return [employee for score, employee in scored[:limit] if score >= 0.55]

    def _ask_policy_sync(self, encrypted_cookie: str, query: str) -> str:
        """Read the published policy text directly instead of asking the LLM to find it."""
        cookie = decrypt_session_cookie(encrypted_cookie, self.config.livekit_api_secret)
        token = self._core_token(cookie)
        policies = self._rows(self._core_json("/api/v1/policies?page=1&page_size=1000", cookie, token))
        if not policies:
            return "There are no published HR policies available in the policy library."

        lowered = query.casefold()
        wants_remote = any(term in lowered for term in ("remote", "work from home", "wfh", "hybrid"))
        if wants_remote:
            matches = [
                policy for policy in policies
                if any(
                    term in (str(policy.get(field) or "").casefold())
                    for field in ("title", "content")
                    for term in ("remote", "work from home", "wfh", "hybrid")
                )
            ]
        else:
            matches = policies
        if not matches:
            titles = ", ".join(str(policy.get("title") or "Untitled policy") for policy in policies[:8])
            return f"I couldn't find a matching policy. Available policies include: {titles}."

        policy = matches[0]
        title = str(policy.get("title") or "HR policy")
        content = str(policy.get("content") or "").strip()
        if not content:
            return f"The policy library contains {title}, but it has no policy text published yet."
        return f"{title}: {content}"

    def _ask_leave_balance_sync(
        self,
        encrypted_cookie: str,
        query: str,
        reference_query: str = "",
    ) -> str:
        """Read current or referenced employee leave balances from Core."""
        cookie = decrypt_session_cookie(encrypted_cookie, self.config.livekit_api_secret)
        token = self._core_token(cookie)
        employees = self._all_employees(cookie, token)
        lowered = query.casefold()
        pronoun_query = any(word in lowered.split() for word in ("his", "her", "their"))
        target_query = reference_query if pronoun_query and reference_query else query
        explicit_self = any(word in lowered.split() for word in ("my", "me", "mine")) and not pronoun_query
        matches = [] if explicit_self else self._employee_matches(employees, target_query, limit=1)

        if matches:
            employee_id = matches[0].get("id")
            if employee_id is None:
                raise HRMSBackendError("matched employee has no numeric id")
            path = f"/api/v1/leave/employees/{employee_id}/balance"
            employee_name = self._employee_label(matches[0]).split(" (")[0]
        elif explicit_self or not self._employee_search_terms(target_query):
            path = "/api/v1/leave/balance/me"
            employee_name = "Your"
        else:
            return f'I couldn\'t identify the employee in "{target_query}". Please provide their name or employee ID.'

        rows = self._rows(self._core_json(path, cookie, token))
        if not rows:
            return f"{employee_name} has no leave balances configured for this year."
        parts: list[str] = []
        for row in rows:
            leave_type = str(row.get("leave_type_name") or "Leave")
            balance = row.get("balance", 0)
            year = row.get("year")
            parts.append(f"{leave_type}: {balance} days remaining" + (f" in {year}" if year else ""))
        prefix = f"{employee_name} leave balance" if employee_name != "Your" else "Your leave balance"
        return prefix + " — " + "; ".join(parts) + "."

    def _ask_pending_leave_requests_sync(self, encrypted_cookie: str, query: str) -> str:
        """List the signed-in user's pending leave requests without requiring an employee ID."""
        cookie = decrypt_session_cookie(encrypted_cookie, self.config.livekit_api_secret)
        token = self._core_token(cookie)
        request_body = self._core_json(
            "/api/v1/leave/requests?" + urlencode({"status": "pending", "page": 1, "page_size": 1000}),
            cookie,
            token,
        )
        requests = self._rows(request_body)
        leave_types = self._rows(self._core_json("/api/v1/leave/types", cookie, token))
        type_names = {
            str(row.get("id")): str(row.get("name") or "Leave")
            for row in leave_types
        }

        lowered = query.casefold()
        casual_only = "casual" in lowered
        current_year = datetime.now(ZoneInfo(self.config.timezone)).year
        year = current_year
        year_match = re.search(r"\b(20\d{2})\b", lowered)
        if year_match:
            year = int(year_match.group(1))

        selected: list[dict[str, object]] = []
        for request in requests:
            leave_name = type_names.get(str(request.get("leave_type_id")), "Leave")
            if casual_only and "casual" not in leave_name.casefold():
                continue
            date_value = str(request.get("start_date") or request.get("created_at") or "")
            if date_value[:4].isdigit() and int(date_value[:4]) != year:
                continue
            selected.append({**request, "leave_type_name": leave_name})

        if not selected:
            label = f"{year} casual leave" if casual_only else f"{year} leave"
            return f"You have no pending {label} requests."

        parts = []
        for request in selected:
            leave_name = str(request.get("leave_type_name") or "Leave")
            start = str(request.get("start_date") or "unknown start date")[:10]
            end = str(request.get("end_date") or start)[:10]
            days = request.get("days")
            duration = f", {days} days" if days not in (None, "") else ""
            parts.append(f"{leave_name} from {start} to {end}{duration}")
        return f"You have {len(parts)} pending leave request" + ("s: " if len(parts) != 1 else ": ") + "; ".join(parts) + "."

    def _ask_manager_count_sync(self, encrypted_cookie: str) -> str:
        cookie = decrypt_session_cookie(encrypted_cookie, self.config.livekit_api_secret)
        token = self._core_token(cookie)
        employees = self._all_employees(cookie, token)
        designation_rows = self._rows(self._core_json("/api/v1/designations", cookie, token))
        designation_names = {
            str(row.get("id")): str(row.get("name") or "")
            for row in designation_rows
        }
        manager_ids = {
            str(employee.get("manager_id"))
            for employee in employees
            if employee.get("manager_id") not in (None, "", 0)
        }
        managers = [
            employee for employee in employees
            if str(employee.get("id")) in manager_ids
            or any(
                marker in str(employee.get("designation_name") or designation_names.get(str(employee.get("designation_id")), "")).casefold()
                for marker in ("manager", "head", "lead")
            )
        ]
        if not managers:
            return "There are no managers in the employee directory."
        names = ", ".join(self._employee_label(employee) for employee in managers)
        return f"There are {len(managers)} managers: {names}."

    def _ask_salary_sync(
        self,
        encrypted_cookie: str,
        query: str,
        reference_query: str = "",
    ) -> str:
        """Read gross amounts from the latest payroll run, honoring Core permissions."""
        cookie = decrypt_session_cookie(encrypted_cookie, self.config.livekit_api_secret)
        token = self._core_token(cookie)
        runs = self._rows(self._core_json("/api/v1/payroll/runs?page=1&page_size=1000", cookie, token))
        if not runs:
            return "There are no payroll runs with gross salary data available."
        latest = max(
            runs,
            key=lambda row: (
                int(row.get("year") or 0),
                int(row.get("month") or 0),
                int(row.get("id") or 0),
            ),
        )
        run_id = latest.get("id")
        if run_id is None:
            raise HRMSBackendError("latest payroll run has no id")
        employees = self._all_employees(cookie, token)
        lowered = query.casefold()
        wants_all = any(term in lowered for term in ("all", "everyone", "each"))
        target_query = reference_query if reference_query and not wants_all else query
        matches = [] if wants_all else self._employee_matches(employees, target_query, limit=1)
        if matches:
            employee_id = matches[0].get("id")
            path = f"/api/v1/payslips?payroll_run_id={run_id}&employee_id={employee_id}"
        elif any(word in lowered.split() for word in ("my", "me", "mine")):
            path = f"/api/v1/payslips/me?payroll_run_id={run_id}"
        elif not self._employee_search_terms(target_query):
            path = f"/api/v1/payslips?payroll_run_id={run_id}"
        else:
            return f'I couldn\'t identify the employee in "{target_query}". Please provide their name or employee ID.'
        payslips = self._rows(self._core_json(path, cookie, token))
        employee_names = {str(employee.get("id")): self._employee_label(employee).split(" (")[0] for employee in employees}
        if not payslips:
            return "No gross salary record is available for the latest payroll run."
        parts = [
            f"{employee_names.get(str(row.get('employee_id')), 'Employee')}: {row.get('gross')}"
            for row in payslips
        ]
        return f"Gross salaries for payroll run {latest.get('month')}/{latest.get('year')}: " + "; ".join(parts) + "."

    def _ask_sync(self, encrypted_cookie: str, query: str) -> str:
        if not encrypted_cookie:
            raise HRMSBackendError("voice session is not linked to an HRMS login")
        if not self.config.livekit_api_secret:
            raise HRMSBackendError("LIVEKIT_API_SECRET is not configured for the voice worker")
        cookie = decrypt_session_cookie(encrypted_cookie, self.config.livekit_api_secret)

        # These are deterministic directory reads. Bypassing the LLM prevents
        # a transient provider/tool-selection failure from turning valid Core
        # data into the generic "unable to retrieve" response.
        intent = self._directory_intent(query)
        if intent:
            try:
                return self._directory_answer_sync(encrypted_cookie, query)
            except HRMSBackendError:
                # Keep the normal AI path as a deployment-compatible fallback
                # when an older Core does not expose one of these reads.
                pass

        try:
            # Let AI perform its normal cookie-to-AI-token exchange. Sending
            # the exchanged token in the `token` field would make the widget
            # treat it as a browser JWT and verify it with JWT_SECRET instead
            # of CORE_SESSION_TOKEN_SECRET.
            with connect(
                self.config.ai_ws_url,
                additional_headers={"Cookie": cookie},
                open_timeout=10,
                close_timeout=5,
            ) as websocket:
                websocket.send(
                    json.dumps(
                        {
                            "token": "",
                            "text": query,
                            "conversation_id": 0,
                            "tz": self.config.timezone,
                            "platform": "voice",
                            "turn_id": uuid.uuid4().hex,
                        }
                    )
                )
                chunks: list[str] = []
                while True:
                    frame = json.loads(websocket.recv(timeout=45))
                    if frame.get("error"):
                        raise HRMSBackendError(str(frame["error"]))
                    if isinstance(frame.get("delta"), str):
                        chunks.append(frame["delta"])
                    if isinstance(frame.get("text"), str):
                        chunks.append(frame["text"])
                    if frame.get("done") or frame.get("text"):
                        break
                answer = "".join(chunks).strip()
                if not answer:
                    raise HRMSBackendError("HRMS AI returned an empty response")
                return answer
        except HRMSBackendError:
            raise
        except Exception as exc:
            raise HRMSBackendError("HRMS AI voice request failed") from exc
