"""Internal WhatsApp-to-existing-HRMS bridge.

This is not a second agent. It reuses the same HRMSBackend and WebSocket AI
service used by agent/agent.py. WhatsApp callers must be mapped to an existing
authenticated HRMS session before private data can be returned.
"""

from __future__ import annotations

import json
import base64
import hashlib
import logging
import os
from typing import Any

from aiohttp import web
from dotenv import load_dotenv

from hr_voice_agent.hrms_backend import HRMSBackend, HRMSBackendConfig, HRMSBackendError

load_dotenv(".env.local")
load_dotenv("agent/.env.local")

logger = logging.getLogger("whatsapp_bridge")
backend = HRMSBackend(HRMSBackendConfig.from_environment())


def _backend_session_cookie(value: str) -> str:
    """Convert a raw browser cookie into the envelope used by HRMSBackend.

    WhatsApp mappings live in the local environment, so storing the raw
    cookie there is acceptable for this development bridge. The shared
    backend still receives the same encrypted v1 envelope used by LiveKit.
    """
    if value.startswith("v1."):
        return value

    # The browser instructions commonly result in copying only the cookie
    # value. Core needs the complete Cookie header, including its name.
    if not value.startswith("hrms_session="):
        value = f"hrms_session={value}"

    api_secret = os.getenv("LIVEKIT_API_SECRET", "")
    if not api_secret:
        raise HRMSBackendError("LIVEKIT_API_SECRET is not configured for WhatsApp HRMS access")

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise HRMSBackendError("cryptography is required for WhatsApp HRMS access") from exc

    key = hashlib.sha256(f"{api_secret}:hrms-session-cookie".encode("utf-8")).digest()
    iv = os.urandom(12)
    encrypted = AESGCM(key).encrypt(iv, value.encode("utf-8"), None)
    ciphertext, tag = encrypted[:-16], encrypted[-16:]
    encode = lambda data: base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")
    return f"v1.{encode(iv)}.{encode(tag)}.{encode(ciphertext)}"


def _phone_map() -> dict[str, dict[str, Any]]:
    raw = os.getenv("WHATSAPP_EMPLOYEE_SESSIONS_JSON", "{}").strip()
    try:
        value = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError("WHATSAPP_EMPLOYEE_SESSIONS_JSON is not valid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError("WHATSAPP_EMPLOYEE_SESSIONS_JSON must be an object")
    return {str(key): item for key, item in value.items() if isinstance(item, dict)}


def _internal_secret_matches(request: web.Request) -> bool:
    expected = os.getenv("WHATSAPP_INTERNAL_SECRET", "").strip()
    return bool(expected) and request.headers.get("x-whatsapp-internal-secret") == expected


async def answer(request: web.Request) -> web.Response:
    if not _internal_secret_matches(request):
        return web.json_response({"error": "Unauthorized internal request"}, status=401)

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    phone = str(body.get("from", "")).strip()
    transcript = str(body.get("transcript", "")).strip()
    if not phone or not transcript:
        return web.json_response({"error": "from and transcript are required"}, status=400)

    identity = _phone_map().get(phone)
    if not identity or not str(identity.get("session_cookie", "")).strip():
        return web.json_response(
            {"error": "This WhatsApp number is not mapped to an authenticated HRMS employee."},
            status=403,
        )

    try:
        answer_text = await backend.ask(
            _backend_session_cookie(str(identity["session_cookie"])),
            transcript,
        )
    except HRMSBackendError:
        logger.exception("Existing HRMS backend failed for mapped WhatsApp user")
        return web.json_response({"error": "The existing HRMS agent could not answer."}, status=502)

    return web.json_response({"answer": answer_text})


async def health(_: web.Request) -> web.Response:
    return web.json_response({"ok": True, "service": "existing-hrms-whatsapp-bridge"})


def create_app() -> web.Application:
    app = web.Application()
    app.add_routes([web.get("/health", health), web.post("/answer", answer)])
    return app


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    port = int(os.getenv("WHATSAPP_AGENT_PORT", "8092"))
    web.run_app(create_app(), host="127.0.0.1", port=port)
