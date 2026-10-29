from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    EMPLOYEE = "employee"
    HR_ADMIN = "hr_admin"


@dataclass(frozen=True)
class Actor:
    user_id: str
    role: Role
    tenant_id: str = ""
    display_name: str = ""
    session_cookie: str = ""


class PermissionDeniedError(PermissionError):
    pass


def require_role(actor: Actor, *allowed: Role) -> None:
    if actor.role not in allowed:
        raise PermissionDeniedError("This operation is not available for your role.")
