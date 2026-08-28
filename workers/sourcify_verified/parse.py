"""Parse Sourcify Parquet rows into RPC JSON payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

TABLE_DEPLOYMENTS = "contract_deployments"
TABLE_VERIFIED = "verified_contracts"

INGEST_ORDER = (TABLE_DEPLOYMENTS, TABLE_VERIFIED)


def normalize_etag(etag: str | None) -> str:
    return (etag or "").strip().strip('"')


def is_file_pending(
    remote_etag: str,
    manifest: dict[str, dict[str, str]],
    *,
    table_name: str,
    file_key: str,
    force: bool,
) -> bool:
    if force:
        return True
    stored = manifest.get(table_name, {}).get(file_key)
    if not stored:
        return True
    return normalize_etag(stored) != normalize_etag(remote_etag)


def build_manifest_index(manifest_rows: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in manifest_rows:
        table = str(row.get("table_name") or "").strip()
        key = str(row.get("file_key") or "").strip()
        etag = normalize_etag(str(row.get("etag") or ""))
        if not table or not key:
            continue
        out.setdefault(table, {})[key] = etag
    return out


def _bytes_to_hex(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return "0x" + value.hex()
    if isinstance(value, bytearray):
        return "0x" + bytes(value).hex()
    text = str(value).strip()
    if not text:
        return None
    if text.startswith("0x") or text.startswith("0X"):
        return "0x" + text[2:].lower()
    if len(text) == 40 and all(c in "0123456789abcdefABCDEF" for c in text):
        return "0x" + text.lower()
    return text.lower()


def normalize_address(value: Any) -> str | None:
    hex_addr = _bytes_to_hex(value)
    if not hex_addr:
        return None
    if not hex_addr.startswith("0x"):
        return None
    body = hex_addr[2:]
    if len(body) != 40:
        return None
    return "0x" + body.lower()


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        if hasattr(value, "item"):
            value = value.item()
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if hasattr(value, "item"):
        value = value.item()
    return bool(value)


def _to_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def parse_deployment_row(row: dict[str, Any]) -> dict[str, Any] | None:
    deployment_id = str(row.get("id") or "").strip()
    chain_id = _to_int(row.get("chain_id"))
    address = normalize_address(row.get("address"))
    contract_id = str(row.get("contract_id") or "").strip() or None
    if not deployment_id or chain_id is None or not address:
        return None
    return {
        "deployment_id": deployment_id,
        "contract_id": contract_id,
        "chain_id": chain_id,
        "address": address,
    }


def parse_verified_row(row: dict[str, Any]) -> dict[str, Any] | None:
    deployment_id = str(row.get("deployment_id") or "").strip()
    if not deployment_id:
        return None
    return {
        "deployment_id": deployment_id,
        "compilation_id": str(row.get("compilation_id") or "").strip() or None,
        "creation_match": _to_bool(row.get("creation_match")),
        "runtime_match": _to_bool(row.get("runtime_match")),
        "creation_metadata_match": _to_bool(row.get("creation_metadata_match")),
        "runtime_metadata_match": _to_bool(row.get("runtime_metadata_match")),
        "sourcify_created_at": _to_iso(row.get("created_at")),
        "sourcify_updated_at": _to_iso(row.get("updated_at")),
    }


def parse_batch(table_name: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    parser = parse_deployment_row if table_name == TABLE_DEPLOYMENTS else parse_verified_row
    for row in rows:
        parsed = parser(row)
        if parsed:
            out.append(parsed)
    return out
