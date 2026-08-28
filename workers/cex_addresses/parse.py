"""Parse Dune Spellbook CEX address VALUES SQL into row dicts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Shared EVM list: (0xaddr, 'cex', 'distinct', 'by', date 'YYYY-MM-DD')
_EVM_TUPLE = re.compile(
    r"\(\s*"
    r"(0x[a-fA-F0-9]{40})\s*,\s*"
    r"'((?:[^'\\]|\\.)*)'\s*,\s*"
    r"'((?:[^'\\]|\\.)*)'\s*,\s*"
    r"'((?:[^'\\]|\\.)*)'\s*,\s*"
    r"date\s+'(\d{4}-\d{2}-\d{2})'\s*"
    r"\)",
    re.IGNORECASE,
)

# Per-chain seed: ('bitcoin', 'addr', 'cex', 'distinct', 'by', date 'YYYY-MM-DD')
_CHAIN_TUPLE = re.compile(
    r"\(\s*"
    r"'((?:[^'\\]|\\.)*)'\s*,\s*"
    r"'((?:[^'\\]|\\.)*)'\s*,\s*"
    r"'((?:[^'\\]|\\.)*)'\s*,\s*"
    r"'((?:[^'\\]|\\.)*)'\s*,\s*"
    r"'((?:[^'\\]|\\.)*)'\s*,\s*"
    r"date\s+'(\d{4}-\d{2}-\d{2})'\s*"
    r"\)",
    re.IGNORECASE,
)

_CEX_EVMS_NAME = "cex_evms_addresses.sql"
_MACRO_MARKER = "cex_evms("


def _unescape_sql_string(value: str) -> str:
    return value.replace("''", "'").replace("\\'", "'")


def _strip_sql_noise(text: str) -> str:
    """Drop Jinja blocks and -- line comments (keep content for VALUES)."""
    text = re.sub(r"\{\{.*?\}\}", "", text, flags=re.DOTALL)
    text = re.sub(r"\{%.*?%\}", "", text, flags=re.DOTALL)
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("--"):
            continue
        # Keep code; inline -- after a quote is rare in these seeds.
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


def is_values_seed_file(path: Path) -> bool:
    """True for curated VALUES seeds; False for cex_evms() wrappers."""
    if path.suffix.lower() != ".sql":
        return False
    name = path.name.lower()
    if name == _CEX_EVMS_NAME:
        return True
    if not name.startswith("cex_") or not name.endswith("_addresses.sql"):
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    if _MACRO_MARKER in text:
        return False
    return "VALUES" in text.upper() or "values" in text


def parse_evm_values(text: str) -> list[dict[str, Any]]:
    clean = _strip_sql_noise(text)
    rows: list[dict[str, Any]] = []
    for m in _EVM_TUPLE.finditer(clean):
        address = m.group(1).lower()
        rows.append(
            {
                "blockchain": "evm",
                "address": address,
                "cex_name": _unescape_sql_string(m.group(2)),
                "distinct_name": _unescape_sql_string(m.group(3)),
                "added_by": _unescape_sql_string(m.group(4)),
                "added_date": m.group(5),
            }
        )
    return rows


def parse_chain_values(text: str) -> list[dict[str, Any]]:
    clean = _strip_sql_noise(text)
    rows: list[dict[str, Any]] = []
    for m in _CHAIN_TUPLE.finditer(clean):
        blockchain = _unescape_sql_string(m.group(1)).strip().lower()
        address = _unescape_sql_string(m.group(2)).strip()
        if blockchain == "evm":
            address = address.lower()
        rows.append(
            {
                "blockchain": blockchain,
                "address": address,
                "cex_name": _unescape_sql_string(m.group(3)),
                "distinct_name": _unescape_sql_string(m.group(4)),
                "added_by": _unescape_sql_string(m.group(5)),
                "added_date": m.group(6),
            }
        )
    return rows


def parse_sql_file(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.name.lower() == _CEX_EVMS_NAME:
        return parse_evm_values(text)
    return parse_chain_values(text)


def collect_cex_rows(addresses_root: Path) -> list[dict[str, Any]]:
    """Walk Spellbook cex/addresses tree and parse all VALUES seeds."""
    if not addresses_root.is_dir():
        raise FileNotFoundError(f"addresses root not found: {addresses_root}")

    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    files = sorted(p for p in addresses_root.rglob("*.sql") if is_values_seed_file(p))
    if not files:
        raise RuntimeError(f"no VALUES seed SQL under {addresses_root}")

    for path in files:
        for row in parse_sql_file(path):
            key = (row["blockchain"], row["address"])
            by_key[key] = row

    return list(by_key.values())


SPELLBOOK_ADDRESSES_REL = (
    "dbt_subprojects/hourly_spellbook/models/_sector/cex/addresses"
)
