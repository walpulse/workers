"""Ingest Dune Spellbook static labels into Walpulse Supabase."""

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
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from supabase import Client, create_client

from workers.spellbook_labels.parse import (
    CEX_ADDRESSES_REL,
    LABELS_ADDRESSES_REL,
    collect_spellbook_label_rows,
)

SPELLBOOK_REPO = "duneanalytics/spellbook"
SPELLBOOK_CLONE_URL = f"https://github.com/{SPELLBOOK_REPO}.git"
MIN_ROWS = 500
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
    data = sb.rpc("get_spellbook_labels_sync_state").execute().data
    if data is None:
        return {}
    if isinstance(data, str):
        return json.loads(data)
    if isinstance(data, dict):
        return data
    return {}


def latest_spellbook_commit(path: str) -> str:
    url = (
        f"{GITHUB_API}/repos/{SPELLBOOK_REPO}/commits"
        f"?path={quote(path)}&per_page=1&sha=main"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "walpulse-workers-spellbook-labels",
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


def composite_source_hash(labels_commit: str, cex_commit: str) -> str:
    raw = f"{labels_commit}:{cex_commit}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def sparse_clone_spellbook(dest: Path) -> tuple[Path, Path]:
    """Shallow sparse clone of labels + cex paths. Returns (labels_root, cex_root)."""
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
    run(
        ["git", "sparse-checkout", "set", LABELS_ADDRESSES_REL, CEX_ADDRESSES_REL],
        cwd=dest,
    )
    labels = dest / LABELS_ADDRESSES_REL
    cex = dest / CEX_ADDRESSES_REL
    if not labels.is_dir():
        raise SystemExit(f"sparse checkout missing {LABELS_ADDRESSES_REL}")
    if not cex.is_dir():
        raise SystemExit(f"sparse checkout missing {CEX_ADDRESSES_REL}")
    return labels, cex


def chunked(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def replace_catalog(sb: Client, rows: list[dict[str, Any]], source_hash: str) -> dict[str, Any]:
    if len(rows) < MIN_ROWS:
        raise SystemExit(f"rows {len(rows)} below safety threshold {MIN_ROWS}")

    print(f"begin ingest: total={len(rows)} hash={source_hash[:16]}…", flush=True)
    sb.rpc("begin_spellbook_labels_ingest").execute()

    for i, batch in enumerate(chunked(rows, APPEND_CHUNK), start=1):
        n = sb.rpc("append_spellbook_labels_ingest", {"p_rows": batch}).execute().data
        print(f"  append chunk {i}: {n} rows", flush=True)

    result = sb.rpc(
        "commit_spellbook_labels_ingest", {"p_source_hash": source_hash}
    ).execute().data
    if isinstance(result, str):
        result = json.loads(result)
    print(f"commit ok: {result}", flush=True)
    return result if isinstance(result, dict) else {"raw": result}


def run(
    *,
    force: bool = False,
    spellbook_dir: Path | None = None,
) -> int:
    sb = supabase_client()
    labels_commit = latest_spellbook_commit(LABELS_ADDRESSES_REL)
    cex_commit = latest_spellbook_commit(CEX_ADDRESSES_REL)
    source_hash = composite_source_hash(labels_commit, cex_commit)
    state = get_sync_state(sb)
    current = (state.get("source_hash") or "").strip()

    print(f"spellbook labels path HEAD: {labels_commit}", flush=True)
    print(f"spellbook cex path HEAD: {cex_commit}", flush=True)
    print(f"composite hash: {source_hash}", flush=True)
    print(f"walpulse sync state: {state or '(empty)'}", flush=True)

    if not force and current and current == source_hash:
        print("catalog unchanged — skip ingest", flush=True)
        return 0

    if force and current == source_hash:
        print("force=true — re-ingest same snapshot", flush=True)

    tmp: Path | None = None
    try:
        if spellbook_dir:
            root = Path(spellbook_dir)
            if not root.is_dir():
                raise SystemExit(f"--spellbook-dir not a directory: {root}")
            labels = root / "labels" / "addresses"
            cex = root / "cex" / "addresses"
            if not labels.is_dir() or not cex.is_dir():
                raise SystemExit(
                    "--spellbook-dir must contain labels/addresses and cex/addresses"
                )
        else:
            tmp = Path(tempfile.mkdtemp(prefix="spellbook-labels-"))
            clone_root = tmp / "spellbook"
            labels, cex = sparse_clone_spellbook(clone_root)

        rows = collect_spellbook_label_rows(labels, cex)
        replace_catalog(sb, rows, source_hash)
    finally:
        if tmp and tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest even if source_hash matches Spellbook HEADs",
    )
    parser.add_argument(
        "--spellbook-dir",
        type=Path,
        default=None,
        help="Local dir with labels/addresses and cex/addresses (skip clone)",
    )
    args = parser.parse_args(argv)
    return run(force=args.force, spellbook_dir=args.spellbook_dir)


if __name__ == "__main__":
    sys.exit(main())
