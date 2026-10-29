import json
import unittest
from unittest.mock import MagicMock, patch

from hr_voice_agent.hrms_backend import HRMSBackend, HRMSBackendConfig


class HRMSBackendTests(unittest.TestCase):
    def _backend(self):
        return HRMSBackend(
            HRMSBackendConfig(
                ai_ws_url="ws://localhost:8083/api/v1/chat/widget",
                core_session_token_url="http://localhost:8081/internal/ai/session-token",
                core_session_token_secret="secret",
                core_api_url="http://localhost:8081",
                livekit_api_secret="livekit-secret",
            )
        )

    def test_parses_spoken_employee_code(self):
        self.assertEqual(
            HRMSBackend._employee_code_from_speech(
                "find a employee with ID e m p zero zero zero zero one one"
            ),
            "EMP-000011",
        )

    def test_employee_search_uses_core_data_without_llm(self):
        backend = self._backend()
        core_responses = {
            "/api/v1/employees?status=active&page=1&page_size=1000": {
                "data": [
                    {
                        "employee_code": "EMP-000011",
                        "first_name": "Shreelakshmi",
                        "last_name": "Employee",
                        "designation_id": 2,
                        "department_id": 1,
                        "status": "active",
                        "hire_date": "2026-05-21",
                    }
                ]
            },
            "/api/v1/departments": {"data": [{"id": 1, "name": "Engineering"}]},
            "/api/v1/designations": {"data": [{"id": 2, "name": "Developer"}]},
        }

        def core_json(path, cookie, token):
            return core_responses[path]

        with (
            patch("hr_voice_agent.hrms_backend.decrypt_session_cookie", return_value="session=ok"),
            patch.object(backend, "_core_token", return_value="core-token"),
            patch.object(backend, "_core_json", side_effect=core_json),
        ):
            answer = backend._ask_employee_search_sync("encrypted", "find e m p zero zero zero zero one one")

        self.assertIn("EMP-000011", answer)
        self.assertIn("Shreelakshmi Employee", answer)
        self.assertIn("Developer", answer)
        self.assertIn("Engineering", answer)

    def test_forwards_cookie_and_leaves_token_empty_for_ai_exchange(self):
        backend = self._backend()
        websocket = MagicMock()
        websocket.recv.return_value = json.dumps({"text": "Your answer", "done": True})
        connection = MagicMock()
        connection.__enter__.return_value = websocket
        with (
            patch("hr_voice_agent.hrms_backend.decrypt_session_cookie", return_value="session=ok"),
            patch("hr_voice_agent.hrms_backend.connect", return_value=connection) as connect,
        ):
            self.assertEqual(backend._ask_sync("encrypted", "hello"), "Your answer")

        self.assertEqual(connect.call_args.kwargs["additional_headers"], {"Cookie": "session=ok"})
        sent = json.loads(websocket.send.call_args.args[0])
        self.assertEqual(sent["token"], "")

    def test_directory_reads_are_grounded_in_core(self):
        backend = self._backend()
        employees = [
            {"id": 1, "employee_code": "EMP-000001", "first_name": "Admin", "last_name": "User"},
            {"id": 2, "employee_code": "EMP-000002", "first_name": "Maya", "last_name": "Patel", "manager_id": 1},
            {"id": 3, "employee_code": "EMP-000003", "first_name": "Ravi", "last_name": "Kumar", "department_id": None},
        ]

        def core_json(path, cookie, token):
            if path.startswith("/api/v1/employees?"):
                return {"data": employees, "meta": {"total": len(employees)}}
            if path == "/api/v1/departments":
                return {"data": [{"id": 10, "name": "Engineering"}]}
            raise AssertionError(path)

        with (
            patch("hr_voice_agent.hrms_backend.decrypt_session_cookie", return_value="session=ok"),
            patch.object(backend, "_core_token", return_value="core-token"),
            patch.object(backend, "_core_json", side_effect=core_json),
        ):
            all_answer = backend._directory_answer_sync("encrypted", "list all employees with their employee IDs")
            unassigned_answer = backend._directory_answer_sync("encrypted", "find all unassigned employees")
            reports_answer = backend._directory_answer_sync("encrypted", "who is working under admin")

        self.assertIn("Maya Patel (EMP-000002)", all_answer)
        self.assertIn("Ravi Kumar (EMP-000003)", unassigned_answer)
        self.assertIn("Maya Patel (EMP-000002)", reports_answer)

    def test_policy_leave_manager_and_salary_reads_are_grounded_in_core(self):
        backend = self._backend()
        employees = [
            {"id": 1, "employee_code": "EMP-000001", "first_name": "Admin", "last_name": "User", "designation_name": "HR Manager"},
            {"id": 2, "employee_code": "EMP-000002", "first_name": "Divya", "last_name": "Employee", "manager_id": 1},
        ]

        def core_json(path, cookie, token):
            if path.startswith("/api/v1/employees?"):
                return {"data": employees, "meta": {"total": len(employees)}}
            if path.startswith("/api/v1/policies?"):
                return {"data": [{"title": "Remote Work Policy", "content": "Employees may work remotely with manager approval."}]}
            if path == "/api/v1/designations":
                return {"data": []}
            if path.startswith("/api/v1/leave/employees/2/balance"):
                return {"data": [{"leave_type_name": "Vacation", "balance": 8, "year": 2026}]}
            if path.startswith("/api/v1/payroll/runs?"):
                return {"data": [{"id": 9, "year": 2026, "month": 8, "status": "paid"}]}
            if path.startswith("/api/v1/payslips?"):
                return {"data": [{"employee_id": 2, "gross": 75000}]}
            raise AssertionError(path)

        with (
            patch("hr_voice_agent.hrms_backend.decrypt_session_cookie", return_value="session=ok"),
            patch.object(backend, "_core_token", return_value="core-token"),
            patch.object(backend, "_core_json", side_effect=core_json),
        ):
            policy = backend._ask_policy_sync("encrypted", "explain the remote work policy")
            balance = backend._ask_leave_balance_sync("encrypted", "how many leaves remain for Divya employee")
            managers = backend._ask_manager_count_sync("encrypted")
            salary = backend._ask_salary_sync("encrypted", "gross salary of Divya employee")

        self.assertIn("Employees may work remotely", policy)
        self.assertIn("Vacation: 8 days remaining", balance)
        self.assertIn("There are 1 managers", managers)
        self.assertIn("Divya Employee: 75000", salary)

    def test_pending_casual_leave_uses_signed_in_user_scope(self):
        backend = self._backend()

        def core_json(path, cookie, token):
            if path.startswith("/api/v1/leave/requests?"):
                return {"data": [{
                    "leave_type_id": 4,
                    "start_date": "2026-09-10",
                    "end_date": "2026-09-11",
                    "days": 2,
                    "status": "pending",
                }]}
            if path == "/api/v1/leave/types":
                return {"data": [{"id": 4, "name": "Casual Leave"}]}
            raise AssertionError(path)

        with (
            patch("hr_voice_agent.hrms_backend.decrypt_session_cookie", return_value="session=ok"),
            patch.object(backend, "_core_token", return_value="core-token"),
            patch.object(backend, "_core_json", side_effect=core_json),
        ):
            answer = backend._ask_pending_leave_requests_sync(
                "encrypted",
                "my pending casual leave list this year",
            )

        self.assertIn("1 pending leave request", answer)
        self.assertIn("Casual Leave from 2026-09-10 to 2026-09-11", answer)


if __name__ == "__main__":
    unittest.main()
