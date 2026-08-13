from __future__ import annotations

import re
from datetime import date


class DateResolutionError(ValueError):
    """A spoken or tool-provided date cannot be used safely."""


def resolve_date_input(value: str, today: date) -> date:
    try:
        if re.fullmatch(r"\d{2}-\d{2}", value):
            month, day = map(int, value.split("-"))
            candidate = date(today.year, month, day)
            return candidate if candidate > today else date(today.year + 1, month, day)

        candidate = date.fromisoformat(value)
    except ValueError as error:
        raise DateResolutionError("Please provide a valid date as MM-DD or YYYY-MM-DD.") from error

    if candidate <= today:
        raise DateResolutionError("The explicitly dated leave request is in the past.")
    return candidate
