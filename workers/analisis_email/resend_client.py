"""Resend HTTP client (stdlib urllib)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


RESEND_EMAILS_URL = "https://api.resend.com/emails"
DEFAULT_FROM = "Walpulse <hello@mail.walpulse.com>"


def _api_key() -> str:
    key = (os.environ.get("RESEND_KEY") or os.environ.get("RESEND_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("missing_resend_key")
    return key


def email_from() -> str:
    return (os.environ.get("EMAIL_FROM") or "").strip() or DEFAULT_FROM


def send_email(
    *,
    to: str,
    subject: str,
    html: str,
    text: str,
    from_addr: str | None = None,
) -> dict[str, Any]:
    """POST /emails. Returns {id: ...} on success. Raises on HTTP/API errors."""
    payload = {
        "from": from_addr or email_from(),
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        RESEND_EMAILS_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "walpulse-analisis-email/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"resend_http_{e.code}: {err_body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"resend_url_error: {e}") from e

    if not isinstance(data, dict) or not data.get("id"):
        raise RuntimeError(f"resend_unexpected_response: {data!r}"[:500])
    return {"id": str(data["id"]), "raw": data}
