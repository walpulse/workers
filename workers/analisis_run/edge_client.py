"""HTTP client for Supabase Edge Functions with aggressive retries (completeness > speed)."""

from __future__ import annotations

import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class EdgeCallResult:
    ok: bool
    status: int
    body: dict[str, Any]


def _env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise SystemExit(f"missing required env: {name}")
    return value


def supabase_url() -> str:
    return _env("SUPABASE_URL").rstrip("/")


def service_role_key() -> str:
    return _env("SUPABASE_SERVICE_ROLE_KEY")


def sleep_ms(ms: float) -> None:
    time.sleep(max(0.0, ms) / 1000.0)


def parse_retry_after_ms(headers: Any, err_msg: str, body: dict[str, Any]) -> float | None:
    if isinstance(body.get("retryAfterMs"), (int, float)):
        return max(0.0, float(body["retryAfterMs"]))
    if headers is not None:
        raw = headers.get("Retry-After") or headers.get("retry-after")
        if raw:
            try:
                return max(0.0, float(raw) * 1000.0)
            except ValueError:
                try:
                    # HTTP-date — ignore precise parse; treat as 5s floor
                    return 5000.0
                except Exception:
                    pass
    m = re.search(r"Retry after\s+(\d+)\s*ms", err_msg, re.I)
    if m:
        return max(0.0, float(m.group(1)))
    s = re.search(r"Retry after\s+(\d+)\s*s", err_msg, re.I)
    if s:
        return max(0.0, float(s.group(1)) * 1000.0)
    return None


def is_retryable(status: int, body: dict[str, Any], err_msg: str = "") -> bool:
    if status in {429, 502, 503, 504}:
        return True
    blob = f"{err_msg} {body.get('error', '')} {body.get('detail', '')} {body.get('message', '')}".lower()
    return any(
        token in blob
        for token in (
            "ratelimit",
            "rate limit",
            "rate_limit",
            "too many requests",
            "worker_limit",
            "timeout",
            "temporar",
        )
    )


def call_edge(
    name: str,
    body: dict[str, Any],
    *,
    timeout_ms: int = 90_000,
    max_attempts: int = 12,
    min_backoff_ms: int = 5_000,
    max_backoff_ms: int = 60_000,
    label: str | None = None,
) -> EdgeCallResult:
    """Invoke `/functions/v1/{name}` with retries on 429/502/503/504/timeouts."""
    url = f"{supabase_url()}/functions/v1/{name}"
    key = service_role_key()
    payload = json.dumps(body).encode("utf-8")
    tag = label or name
    last = EdgeCallResult(ok=False, status=0, body={"error": "no_attempt"})

    for attempt in range(1, max_attempts + 1):
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {key}",
                "apikey": key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_ms / 1000.0) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    parsed = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    parsed = {"error": "invalid_json_response", "raw": raw[:300]}
                if not isinstance(parsed, dict):
                    parsed = {"data": parsed}
                status = getattr(resp, "status", 200) or 200
                result = EdgeCallResult(ok=200 <= status < 300, status=status, body=parsed)
                if result.ok:
                    return result
                last = result
                if not is_retryable(status, parsed) or attempt >= max_attempts:
                    return result
                wait = parse_retry_after_ms(resp.headers, str(parsed), parsed)
                if wait is None:
                    wait = min(max_backoff_ms, min_backoff_ms * (2 ** (attempt - 1)))
                    wait = wait * (0.8 + random.random() * 0.4)
                print(f"edge_retry name={tag} attempt={attempt} status={status} wait_ms={int(wait)}")
                sleep_ms(wait)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = {"error": raw[:300] or f"http_{e.code}"}
            if not isinstance(parsed, dict):
                parsed = {"error": str(parsed)}
            last = EdgeCallResult(ok=False, status=e.code, body=parsed)
            if not is_retryable(e.code, parsed, raw) or attempt >= max_attempts:
                return last
            wait = parse_retry_after_ms(e.headers, raw, parsed)
            if wait is None:
                wait = min(max_backoff_ms, min_backoff_ms * (2 ** (attempt - 1)))
                wait = wait * (0.8 + random.random() * 0.4)
            print(f"edge_retry name={tag} attempt={attempt} status={e.code} wait_ms={int(wait)}")
            sleep_ms(wait)
        except Exception as e:  # noqa: BLE001 — timeout / network
            msg = str(e)
            last = EdgeCallResult(ok=False, status=0, body={"error": "transport_error", "detail": msg[:300]})
            if attempt >= max_attempts or not is_retryable(504, last.body, msg):
                return last
            wait = min(max_backoff_ms, min_backoff_ms * (2 ** (attempt - 1)))
            print(f"edge_retry name={tag} attempt={attempt} transport wait_ms={int(wait)} detail={msg[:80]}")
            sleep_ms(wait)

    return last
