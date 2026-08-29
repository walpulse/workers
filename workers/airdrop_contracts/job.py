"""Ingest airdrop claim/distributor contracts into Walpulse Supabase."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from supabase import Client, create_client

from workers.airdrop_contracts.merge import merge_rows
from workers.airdrop_contracts.parse_curated import load_curated_contracts
from workers.airdrop_contracts.parse_factories import (
    _cursor_key,
    collect_factory_clones,
)
from workers.airdrop_contracts.parse_spellbook import (
    collect_spellbook_metadata,
    enrich_rows_with_spellbook,
)
from workers.airdrop_contracts.validate_onchain import validate_rows

PKG_DIR = Path(__file__).resolve().parent
SPELLBOOK_REPO = "duneanalytics/spellbook"
SPELLBOOK_CLONE_URL = f"https://github.com/{SPELLBOOK_REPO}.git"
SPARSE_PATHS = ("models/_sector/airdrops",)
MIN_ROWS = 10
APPEND_CHUNK = 500


def _env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise SystemExit(f"missing required env: {name}")
    return value


def supabase_client() -> Client:
    return create_client(_env("SUPABASE_URL"), _env("SUPABASE_SERVICE_ROLE_KEY"))


def get_sync_state(sb: Client) -> dict[str, Any]:
    data = sb.rpc("get_airdrop_contracts_sync_state").execute().data
    if data is None:
        return {}
    if isinstance(data, str):
        return json.loads(data)
    if isinstance(data, dict):
        return data
    return {}


def get_factory_cursors(sb: Client) -> dict[str, int]:
    data = sb.rpc("get_airdrop_factory_scan_cursors").execute().data
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, list):
        return {}
    out: dict[str, int] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        chain = str(row.get("blockchain") or "").strip().lower()
        addr = str(row.get("factory_address") or "").strip().lower()
        if not chain or not addr:
            continue
        out[_cursor_key(chain, addr)] = int(row.get("last_scanned_block") or 0)
    return out


def get_existing_factory_clones(sb: Client) -> list[dict[str, Any]]:
    data = sb.rpc("get_airdrop_factory_clone_rows").execute().data
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, list):
        return []
    rows: list[dict[str, Any]] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "blockchain": str(row.get("blockchain") or "").strip().lower(),
                "address": str(row.get("address") or "").strip().lower(),
                "project_slug": str(row.get("project_slug") or "sablier"),
                "project_name": str(row.get("project_name") or "Sablier Airdrops"),
                "token_address": row.get("token_address"),
                "token_symbol": row.get("token_symbol"),
                "source": "factory_clone",
                "factory_address": row.get("factory_address"),
                "notes": row.get("notes"),
                "raw": row.get("raw") or {},
            }
        )
    return [r for r in rows if r["blockchain"] and r["address"]]


def upsert_factory_cursors(sb: Client, updates: list[dict[str, Any]]) -> None:
    if not updates:
        return
    n = sb.rpc("upsert_airdrop_factory_scan_cursors", {"p_rows": updates}).execute().data
    print(f"factory cursors upserted: {n}", flush=True)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_source_hash(
    *,
    contracts_yaml: str,
    factories_yaml: str,
    clone_keys: list[str],
) -> str:
    clones = "|".join(sorted(clone_keys))
    parts = [
        f"contracts:{sha256_text(contracts_yaml)}",
        f"factories:{sha256_text(factories_yaml)}",
        f"clones:{sha256_text(clones)}",
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def chunked(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def sparse_clone_spellbook(dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    def run(args: list[str], cwd: Path | None = None) -> None:
        print("+", " ".join(args), flush=True)
        subprocess.run(args, cwd=cwd, check=True)

    run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--filter=blob:none",
            "--sparse",
            SPELLBOOK_CLONE_URL,
            str(dest),
        ]
    )
    run(["git", "sparse-checkout", "set", *SPARSE_PATHS], cwd=dest)
    return dest


def rows_for_rpc(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip None-friendly fields to JSON-safe ingest payloads."""
    out: list[dict[str, Any]] = []
    for r in rows:
        item = {
            "blockchain": r["blockchain"],
            "address": r["address"],
            "project_slug": r["project_slug"],
            "project_name": r["project_name"],
            "source": r["source"],
            "raw": r.get("raw") or {},
        }
        if r.get("token_address"):
            item["token_address"] = r["token_address"]
        if r.get("token_symbol"):
            item["token_symbol"] = r["token_symbol"]
        if r.get("factory_address"):
            item["factory_address"] = r["factory_address"]
        if r.get("notes"):
            item["notes"] = r["notes"]
        out.append(item)
    return out


def replace_catalog(sb: Client, rows: list[dict[str, Any]], source_hash: str) -> dict[str, Any]:
    if len(rows) < MIN_ROWS:
        raise SystemExit(f"rows {len(rows)} below safety threshold {MIN_ROWS}")

    payload = rows_for_rpc(rows)
    print(f"begin ingest: total={len(payload)} hash={source_hash[:12]}…", flush=True)
    sb.rpc("begin_airdrop_contracts_ingest").execute()

    for i, batch in enumerate(chunked(payload, APPEND_CHUNK), start=1):
        n = sb.rpc("append_airdrop_contracts_ingest", {"p_rows": batch}).execute().data
        print(f"  append chunk {i}: {n} rows", flush=True)

    result = sb.rpc(
        "commit_airdrop_contracts_ingest", {"p_source_hash": source_hash}
    ).execute().data
    if isinstance(result, str):
        result = json.loads(result)
    print(f"commit ok: {result}", flush=True)
    return result if isinstance(result, dict) else {"raw": result}


def run(
    *,
    force: bool = False,
    skip_factories: bool = False,
    skip_spellbook: bool = False,
    skip_validate: bool = False,
    contracts_path: Path | None = None,
    factories_path: Path | None = None,
    spellbook_dir: Path | None = None,
    max_factory_blocks: int | None = None,
) -> int:
    sb = supabase_client()
    state = get_sync_state(sb)
    current = (state.get("source_hash") or "").strip()

    contracts_file = contracts_path or (PKG_DIR / "contracts.yaml")
    factories_file = factories_path or (PKG_DIR / "factories.yaml")
    contracts_yaml = contracts_file.read_text(encoding="utf-8")
    factories_yaml = factories_file.read_text(encoding="utf-8")

    curated = load_curated_contracts(contracts_file)
    print(f"curated rows: {len(curated)}", flush=True)

    existing_clones: list[dict[str, Any]] = []
    new_clones: list[dict[str, Any]] = []
    factory_warnings: list[str] = []
    cursor_updates: list[dict[str, Any]] = []

    if skip_factories:
        print("factories: skipped (--skip-factories)", flush=True)
        existing_clones = get_existing_factory_clones(sb)
        print(f"kept existing factory clones: {len(existing_clones)}", flush=True)
    else:
        cursors = {} if force else get_factory_cursors(sb)
        if force:
            print("factories: full rescan (--force)", flush=True)
        else:
            print(f"factories: incremental cursors={len(cursors)}", flush=True)
        existing_clones = [] if force else get_existing_factory_clones(sb)
        if existing_clones:
            print(f"existing factory clones: {len(existing_clones)}", flush=True)
        new_clones, factory_warnings, cursor_updates = collect_factory_clones(
            factories_path=factories_file,
            max_blocks_per_factory=max_factory_blocks,
            cursors=cursors,
            force_full_rescan=force,
        )
        for w in factory_warnings:
            print(f"WARN {w}", flush=True)
        print(f"new factory clones this run: {len(new_clones)}", flush=True)

    factory_rows = merge_rows(existing_clones, new_clones)
    merged = merge_rows(curated, factory_rows)

    tmp: Path | None = None
    try:
        if not skip_spellbook:
            try:
                if spellbook_dir:
                    repo_root = Path(spellbook_dir)
                else:
                    tmp = Path(tempfile.mkdtemp(prefix="walpulse-airdrop-sb-"))
                    repo_root = sparse_clone_spellbook(tmp / "spellbook")
                meta = collect_spellbook_metadata(repo_root)
                print(f"spellbook metadata entries: {len(meta)}", flush=True)
                merged = enrich_rows_with_spellbook(merged, meta)
            except Exception as exc:  # noqa: BLE001 — enrichment is best-effort
                print(f"WARN spellbook enrichment skipped: {exc}", flush=True)
        else:
            print("spellbook: skipped", flush=True)

        if skip_validate:
            accepted, rejected = merged, []
        else:
            accepted, rejected = validate_rows(merged)
        print(f"validated: accepted={len(accepted)} rejected={len(rejected)}", flush=True)
        for r in rejected[:20]:
            print(
                f"  rejected {r.get('blockchain')} {r.get('address')} "
                f"({r.get('reject_reason')})",
                flush=True,
            )

        clone_keys = [
            f"{r['blockchain']}:{r['address']}"
            for r in accepted
            if r.get("source") == "factory_clone"
        ]
        source_hash = compute_source_hash(
            contracts_yaml=contracts_yaml,
            factories_yaml=factories_yaml,
            clone_keys=clone_keys,
        )
        print(f"source hash: {source_hash}", flush=True)
        print(f"walpulse sync state: {state or '(empty)'}", flush=True)

        # Advance cursors even when catalog unchanged (avoid re-paying CU).
        if cursor_updates:
            upsert_factory_cursors(sb, cursor_updates)

        if not force and current and current == source_hash:
            print("catalog unchanged — skip ingest", flush=True)
            return 0

        replace_catalog(sb, accepted, source_hash)
        return 0
    finally:
        if tmp and tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Full factory log rescan from YAML from_block + re-ingest even if hash matches",
    )
    parser.add_argument("--skip-factories", action="store_true")
    parser.add_argument("--skip-spellbook", action="store_true")
    parser.add_argument("--skip-validate", action="store_true")
    parser.add_argument("--contracts-path", type=Path, default=None)
    parser.add_argument("--factories-path", type=Path, default=None)
    parser.add_argument("--spellbook-dir", type=Path, default=None)
    parser.add_argument(
        "--max-factory-blocks",
        type=int,
        default=None,
        help="Limit log scan window per factory (tests / slow RPCs)",
    )
    args = parser.parse_args(argv)
    return run(
        force=args.force,
        skip_factories=args.skip_factories,
        skip_spellbook=args.skip_spellbook,
        skip_validate=args.skip_validate,
        contracts_path=args.contracts_path,
        factories_path=args.factories_path,
        spellbook_dir=args.spellbook_dir,
        max_factory_blocks=args.max_factory_blocks,
    )


if __name__ == "__main__":
    sys.exit(main())
