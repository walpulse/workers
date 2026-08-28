"""Ingest Dune Spellbook CEX addresses into Walpulse Supabase."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from supabase import Client, create_client

from workers.cex_addresses.parse import SPELLBOOK_ADDRESSES_REL, collect_cex_rows

SPELLBOOK_REPO = "duneanalytics/spellbook"
SPELLBOOK_CLONE_URL = f"https://github.com/{SPELLBOOK_REPO}.git"
MIN_EVM_ROWS = 1000
APPEND_CHUNK = 500
GITHUB_API = "https://api.github.com"


def _env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise SystemExit(f"missing required env: {name}")
    return value


def supabase_client() -> Client:
    return create_client(_env("SUPABASE_URL"), _env("SUPABASE_SERVICE_ROLE_KEY"))


def get_sync_state(sb: Client) -> dict[str, Any]:
    data = sb.rpc("get_cex_addresses_sync_state").execute().data
    if data is None:
        return {}
    if isinstance(data, str):
        return json.loads(data)
    if isinstance(data, dict):
        return data
    return {}


def latest_spellbook_commit(path: str = SPELLBOOK_ADDRESSES_REL) -> str:
    """Latest commit SHA that touched the CEX addresses directory on main."""
    url = (
        f"{GITHUB_API}/repos/{SPELLBOOK_REPO}/commits"
        f"?path={quote(path)}&per_page=1&sha=main"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "walpulse-workers-cex-addresses",
    }
    token = (os.environ.get("GITHUB_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        raise SystemExit(f"GitHub commits API failed: HTTP {e.code}") from e
    except URLError as e:
        raise SystemExit(f"GitHub commits API failed: {e}") from e

    if not payload or not isinstance(payload, list):
        raise SystemExit("GitHub commits API returned empty list")
    sha = payload[0].get("sha")
    if not sha:
        raise SystemExit("GitHub commits API missing sha")
    return str(sha)


def sparse_clone_spellbook(dest: Path) -> Path:
    """Shallow sparse clone of Spellbook CEX addresses only. Returns addresses root."""
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
    run(["git", "sparse-checkout", "set", SPELLBOOK_ADDRESSES_REL], cwd=dest)
    addresses = dest / SPELLBOOK_ADDRESSES_REL
    if not addresses.is_dir():
        raise SystemExit(f"sparse checkout missing {SPELLBOOK_ADDRESSES_REL}")
    return addresses


def chunked(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def replace_catalog(sb: Client, rows: list[dict[str, Any]], commit: str) -> dict[str, Any]:
    evm_n = sum(1 for r in rows if r["blockchain"] == "evm")
    if evm_n < MIN_EVM_ROWS:
        raise SystemExit(f"evm rows {evm_n} below safety threshold {MIN_EVM_ROWS}")

    print(f"begin ingest: total={len(rows)} evm={evm_n} commit={commit}", flush=True)
    sb.rpc("begin_cex_addresses_ingest").execute()

    for i, batch in enumerate(chunked(rows, APPEND_CHUNK), start=1):
        n = sb.rpc("append_cex_addresses_ingest", {"p_rows": batch}).execute().data
        print(f"  append chunk {i}: {n} rows", flush=True)

    result = sb.rpc("commit_cex_addresses_ingest", {"p_commit": commit}).execute().data
    if isinstance(result, str):
        result = json.loads(result)
    print(f"commit ok: {result}", flush=True)
    return result if isinstance(result, dict) else {"raw": result}


def run(*, force: bool = False, spellbook_dir: Path | None = None) -> int:
    sb = supabase_client()
    remote_sha = latest_spellbook_commit()
    state = get_sync_state(sb)
    current = (state.get("source_commit") or "").strip()

    print(f"spellbook cex path HEAD: {remote_sha}", flush=True)
    print(f"walpulse sync state: {state or '(empty)'}", flush=True)

    if not force and current and current == remote_sha:
        print("catalog unchanged — skip ingest", flush=True)
        return 0

    if force and current == remote_sha:
        print("force=true — re-ingest same commit", flush=True)

    tmp: Path | None = None
    try:
        if spellbook_dir:
            addresses = Path(spellbook_dir)
            if not addresses.is_dir():
                raise SystemExit(f"--spellbook-dir not a directory: {addresses}")
        else:
            tmp = Path(tempfile.mkdtemp(prefix="spellbook-cex-"))
            addresses = sparse_clone_spellbook(tmp / "spellbook")

        rows = collect_cex_rows(addresses)
        replace_catalog(sb, rows, remote_sha)
    finally:
        if tmp and tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest even if source_commit matches Spellbook HEAD",
    )
    parser.add_argument(
        "--spellbook-dir",
        type=Path,
        default=None,
        help="Local path to …/cex/addresses (skip clone; still uses GitHub SHA)",
    )
    args = parser.parse_args(argv)
    return run(force=args.force, spellbook_dir=args.spellbook_dir)


if __name__ == "__main__":
    sys.exit(main())
