"""Load curated airdrop claim contracts from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PKG_DIR = Path(__file__).resolve().parent
DEFAULT_CONTRACTS_PATH = PKG_DIR / "contracts.yaml"

ADDR_RE_LEN = 42  # 0x + 40 hex


def _norm_addr(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if not text.startswith("0x") or len(text) != ADDR_RE_LEN:
        return None
    try:
        int(text[2:], 16)
    except ValueError:
        return None
    return text


def load_curated_contracts(path: Path | None = None) -> list[dict[str, Any]]:
    """Return ingest-ready rows with source=walpulse_curated."""
    yaml_path = path or DEFAULT_CONTRACTS_PATH
    payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    rows_in = payload.get("contracts") or []
    out: list[dict[str, Any]] = []
    for raw in rows_in:
        if not isinstance(raw, dict):
            continue
        address = _norm_addr(raw.get("address"))
        blockchain = str(raw.get("blockchain") or "").strip().lower()
        slug = str(raw.get("project_slug") or "").strip()
        name = str(raw.get("project_name") or "").strip()
        if not address or not blockchain or not slug or not name:
            continue
        if slug.startswith("_"):
            continue
        token = _norm_addr(raw.get("token_address"))
        out.append(
            {
                "blockchain": blockchain,
                "address": address,
                "project_slug": slug,
                "project_name": name,
                "token_address": token,
                "token_symbol": (str(raw.get("token_symbol") or "").strip() or None),
                "source": "walpulse_curated",
                "factory_address": None,
                "notes": (str(raw.get("notes") or "").strip() or None),
                "raw": {"curated": True},
            }
        )
    return out
