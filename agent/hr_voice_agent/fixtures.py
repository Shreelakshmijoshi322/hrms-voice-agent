from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FixtureNotFoundError(LookupError):
    """A requested fictional HRMS record does not exist."""


class FixtureRepository:
    def __init__(self, path: Path | None = None) -> None:
        fixture_path = path or Path(__file__).parents[2] / "data" / "hrms-fixtures.json"
        self._data = json.loads(fixture_path.read_text(encoding="utf-8"))

    def company(self) -> dict[str, Any]:
        return self._data["company"]

    def employee(self, employee_id: str) -> dict[str, Any]:
        try:
            return next(
                item
                for item in self._data["employees"]
                if item["employee_id"] == employee_id
            )
        except StopIteration as error:
            raise FixtureNotFoundError("That employee was not found in the demo directory.") from error

    def payslip(self, employee_id: str) -> dict[str, Any]:
        try:
            return self._data["payslips"][employee_id]
        except KeyError as error:
            raise FixtureNotFoundError("No demo payslip was found for that employee.") from error

    def calendar(self, employee_id: str) -> list[dict[str, Any]]:
        try:
            return self._data["calendar_events"][employee_id]
        except KeyError as error:
            raise FixtureNotFoundError("No demo calendar was found for that employee.") from error

    def holidays(self, location: str) -> list[dict[str, Any]]:
        return [
            holiday
            for holiday in self._data["holidays"]
            if location in holiday["locations"]
        ]

    def hr_contacts(self) -> list[dict[str, Any]]:
        return self._data["hr_contacts"]

    def employees(self) -> list[dict[str, Any]]:
        return self._data["employees"]

    def leave_balance(self, employee_id: str) -> dict[str, int]:
        try:
            return self._data["leave_balances"][employee_id]
        except KeyError as error:
            raise FixtureNotFoundError("No demo leave balance was found for that employee.") from error

    def tasks(self, employee_id: str) -> list[dict[str, Any]]:
        try:
            return self._data["tasks"][employee_id]
        except KeyError as error:
            raise FixtureNotFoundError("No demo tasks were found for that employee.") from error

    def learning_programs(self) -> list[dict[str, Any]]:
        return self._data["learning_programs"]

    def search(self, query: str) -> list[dict[str, Any]]:
        needle = query.casefold()
        return [
            policy
            for policy in self._data["policies"]
            if needle in policy["title"].casefold()
            or any(needle in keyword.casefold() for keyword in policy["keywords"])
            or needle in policy["summary"].casefold()
        ]
