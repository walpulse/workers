"""Ingest CoinGecko token taxonomy into Walpulse Supabase."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from supabase import Client, create_client

from workers.token_taxonomy.parse import collect_token_taxonomy_rows

MIN_ROWS = 1000
APPEND_CHUNK = 500


def _env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise SystemExit(f"missing required env: {name}")
    return value


def supabase_client() -> Client:
    return create_client(_env("SUPABASE_URL"), _env("SUPABASE_SERVICE_ROLE_KEY"))


def get_sync_state(sb: Client) -> dict[str, Any]:
    data = sb.rpc("get_token_taxonomy_sync_state").execute().data
    if data is None:
        return {}
    if isinstance(data, str):
        return json.loads(data)
    if isinstance(data, dict):
        return data
    return {}


def chunked(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def replace_catalog(sb: Client, rows: list[dict[str, Any]], source_hash: str) -> dict[str, Any]:
    if len(rows) < MIN_ROWS:
        raise SystemExit(f"rows {len(rows)} below safety threshold {MIN_ROWS}")

    print(f"begin ingest: total={len(rows)} hash={source_hash[:16]}…", flush=True)
    sb.rpc("begin_token_taxonomy_ingest").execute()

    for i, batch in enumerate(chunked(rows, APPEND_CHUNK), start=1):
        n = sb.rpc("append_token_taxonomy_ingest", {"p_rows": batch}).execute().data
        print(f"  append chunk {i}: {n} rows", flush=True)

    result = sb.rpc(
        "commit_token_taxonomy_ingest", {"p_source_hash": source_hash}
    ).execute().data
    if isinstance(result, str):
        result = json.loads(result)
    print(f"commit ok: {result}", flush=True)
    return result if isinstance(result, dict) else {"raw": result}


def run(*, force: bool = False) -> int:
    api_key = _env("COINGECKO_KEY")
    sb = supabase_client()

    print("fetching CoinGecko taxonomy…", flush=True)
    rows, source_hash, stats = collect_token_taxonomy_rows(api_key)
    print(f"parsed rows={len(rows)} stats={stats}", flush=True)

    state = get_sync_state(sb)
    current = (state.get("source_hash") or "").strip()
    print(f"source hash: {source_hash}", flush=True)
    print(f"walpulse sync state: {state or '(empty)'}", flush=True)

    if not force and current and current == source_hash:
        print("catalog unchanged — skip ingest", flush=True)
        return 0

    if force and current == source_hash:
        print("force=true — re-ingest same snapshot", flush=True)

    replace_catalog(sb, rows, source_hash)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest even if source_hash matches last sync",
    )
    args = parser.parse_args(argv)
    return run(force=args.force)


if __name__ == "__main__":
    sys.exit(main())
