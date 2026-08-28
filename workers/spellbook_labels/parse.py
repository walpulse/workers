"""Parse Dune Spellbook static labels (VALUES + CEX mapped) into row dicts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from workers.cex_addresses.parse import collect_cex_rows

LABELS_ADDRESSES_REL = (
    "dbt_subprojects/daily_spellbook/models/_sector/labels/addresses"
)
CEX_ADDRESSES_REL = "dbt_subprojects/hourly_spellbook/models/_sector/cex/addresses"

_UNION_BASENAMES = frozenset(
    {
        "labels_bridges.sql",
        "labels_cex.sql",
        "labels_dao.sql",
        "labels_dex.sql",
        "labels_infrastructure.sql",
        "labels_nft.sql",
        "labels_social.sql",
    }
)

_EVM_CHAINS = frozenset(
    {
        "ethereum",
        "arbitrum",
        "optimism",
        "polygon",
        "bnb",
        "avalanche_c",
        "fantom",
        "gnosis",
        "base",
        "zkevm",
        "evm",
    }
)


def _unescape_sql_string(value: str) -> str:
    return value.replace("''", "'").replace("\\'", "'")


def _strip_sql_noise(text: str) -> str:
    text = re.sub(r"\{\{.*?\}\}", "", text, flags=re.DOTALL)
    text = re.sub(r"\{%.*?%\}", "", text, flags=re.DOTALL)
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("--"):
            continue
        if "--" in line:
            in_single = False
            out: list[str] = []
            i = 0
            while i < len(line):
                ch = line[i]
                if ch == "'" and not in_single:
                    in_single = True
                    out.append(ch)
                elif ch == "'" and in_single:
                    in_single = False
                    out.append(ch)
                elif ch == "-" and not in_single and i + 1 < len(line) and line[i + 1] == "-":
                    break
                else:
                    out.append(ch)
                i += 1
            lines.append("".join(out))
        else:
            lines.append(line)
    return "\n".join(lines)


def _normalize_address(blockchain: str, address: str) -> str:
    chain = blockchain.strip().lower()
    addr = address.strip()
    if chain in _EVM_CHAINS and addr.lower().startswith("0x"):
        return addr.lower()
    return addr


def _parse_timestamp(date_part: str | None, ts_part: str | None) -> str | None:
    raw = ts_part or date_part
    if not raw:
        return None
    raw = raw.strip()
    if len(raw) == 10:
        return f"{raw}T00:00:00Z"
    if " " in raw and "T" not in raw:
        return raw.replace(" ", "T") + "Z"
    if not raw.endswith("Z") and "T" in raw:
        return raw + "Z"
    return raw


def row_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        row["blockchain"],
        row["address"],
        row["name"],
        row["category"],
        row["model_name"],
    )


def should_skip_label_file(path: Path) -> bool:
    """Skip union wrappers, per-chain cex label SQL, and query-only models."""
    name = path.name.lower()
    if name in _UNION_BASENAMES:
        return True
    if name.startswith("labels_cex_") and name.endswith(".sql"):
        return True

    text = path.read_text(encoding="utf-8", errors="replace")
    upper = text.upper()
    if "VALUES" not in upper:
        return True

    if re.search(r"from\s+\{\{\s*source\(\s*'(?:ethereum|gnosis|arbitrum|bnb|optimism|avalanche_c|fantom)'", text, re.IGNORECASE):
        return True
    if re.search(r"from\s+\{\{\s*ref\(", text, re.IGNORECASE) and "VALUES" not in upper:
        return True
    return False


def parse_label_values(text: str) -> list[dict[str, Any]]:
    return _parse_label_values_fixed(_strip_sql_noise(text))


def _parse_label_values_fixed(clean: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pattern = re.compile(
        r"\(\s*"
        r"'((?:[^'\\]|\\.)*)'\s*,\s*"
        r"(?:'(0x[a-fA-F0-9]{40})'|(0x[a-fA-F0-9]{40})|'((?:[^'\\]|\\.)*)')\s*,\s*"
        r"'((?:[^'\\]|\\.)*)'\s*,\s*"
        r"'((?:[^'\\]|\\.)*)'\s*,\s*"
        r"'((?:[^'\\]|\\.)*)'\s*,\s*"
        r"'((?:[^'\\]|\\.)*)'\s*,\s*"
        r"(?:timestamp\s+'(\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}:\d{2})?)'"
        r"|date\s+'(\d{4}-\d{2}-\d{2})')\s*,\s*"
        r"(?:now\s*\(\s*\)|timestamp\s+'(\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}:\d{2})?)')\s*,\s*"
        r"'((?:[^'\\]|\\.)*)'\s*,\s*"
        r"'((?:[^'\\]|\\.)*)'\s*"
        r"\)",
        re.IGNORECASE,
    )
    for m in pattern.finditer(clean):
        blockchain = _unescape_sql_string(m.group(1)).strip().lower()
        address_raw = m.group(2) or m.group(3) or m.group(4) or ""
        address = _normalize_address(blockchain, address_raw)
        created = _parse_timestamp(m.group(10), m.group(9))
        updated_raw = m.group(11)
        updated = _parse_timestamp(None, updated_raw) if updated_raw else None
        rows.append(
            {
                "blockchain": blockchain,
                "address": address,
                "name": _unescape_sql_string(m.group(5)),
                "category": _unescape_sql_string(m.group(6)),
                "contributor": _unescape_sql_string(m.group(7)),
                "source": _unescape_sql_string(m.group(8)),
                "created_at": created,
                "updated_at": updated,
                "model_name": _unescape_sql_string(m.group(12)),
                "label_type": _unescape_sql_string(m.group(13)),
            }
        )
    return rows


def cex_rows_to_labels(cex_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in cex_rows:
        chain = row["blockchain"]
        created = row.get("added_date")
        created_at = f"{created}T00:00:00Z" if created else None
        out.append(
            {
                "blockchain": chain,
                "address": row["address"],
                "name": row["distinct_name"],
                "category": "institution",
                "contributor": row.get("added_by") or "",
                "source": "static",
                "created_at": created_at,
                "updated_at": None,
                "model_name": f"cex_{chain}",
                "label_type": "identifier",
            }
        )
    return out


def collect_spellbook_label_rows(
    labels_root: Path,
    cex_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Walk Spellbook labels/addresses (+ optional cex/addresses) and parse static rows."""
    if not labels_root.is_dir():
        raise FileNotFoundError(f"labels root not found: {labels_root}")

    by_key: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}

    for path in sorted(labels_root.rglob("*.sql")):
        if should_skip_label_file(path):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rows = parse_label_values(text)
        for row in rows:
            by_key[row_key(row)] = row

    if cex_root and cex_root.is_dir():
        for row in cex_rows_to_labels(collect_cex_rows(cex_root)):
            by_key[row_key(row)] = row

    if not by_key:
        raise RuntimeError(f"no static label rows under {labels_root}")

    return list(by_key.values())
