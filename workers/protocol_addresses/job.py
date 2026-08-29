"""Ingest DeFi protocol contract addresses into Walpulse Supabase."""

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
from urllib.request import Request, urlopen

from supabase import Client, create_client

from workers.protocol_addresses.parse import (
    DEFAULT_OFFICIAL_SEED,
    LABELS_ADDRESSES_REL,
    collect_protocol_rows,
)

MIN_TOTAL_ROWS = 50
APPEND_CHUNK = 500
GITHUB_API = "https://api.github.com"
SPELLBOOK_REPO = "duneanalytics/spellbook"
DEFILLAMA_ADAPTERS_REPO = "DefiLlama/DefiLlama-Adapters"

# P2 gated allowlist — high-TVL / Origins-relevant only
DEFAULT_DEFILLAMA_ALLOWLIST = frozenset(
    {
        "uniswap",
        "aave-v3",
        "aave",
        "compound-v3",
        "lido",
        "curve-dex",
        "curve",
        "1inch",
        "cowswap",
        "balancer",
        "sushiswap",
    }
)


def _env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise SystemExit(f"missing required env: {name}")
    return value


def supabase_client() -> Client:
    return create_client(_env("SUPABASE_URL"), _env("SUPABASE_SERVICE_ROLE_KEY"))


def get_sync_state(sb: Client) -> dict[str, Any]:
    data = sb.rpc("get_protocol_addresses_sync_state").execute().data
    if data is None:
        return {}
    if isinstance(data, str):
        return json.loads(data)
    if isinstance(data, dict):
        return data
    return {}


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "walpulse-workers-protocol-addresses",
    }
    token = (os.environ.get("GITHUB_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def latest_github_commit(repo: str, path: str, *, branch: str = "main") -> str:
    url = (
        f"{GITHUB_API}/repos/{repo}/commits"
        f"?path={path}&per_page=1&sha={branch}"
    )
    req = Request(url, headers=_github_headers())
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


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def sparse_clone(repo: str, dest: Path, sparse_paths: tuple[str, ...], *, branch: str = "main") -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    def run(args: list[str], cwd: Path | None = None) -> None:
        print("+", " ".join(args), flush=True)
        subprocess.run(args, cwd=cwd, check=True)

    clone_url = f"https://github.com/{repo}.git"
    run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--filter=blob:none",
            "--sparse",
            "--branch",
            branch,
            clone_url,
            str(dest),
        ]
    )
    run(["git", "sparse-checkout", "set", *sparse_paths], cwd=dest)


def chunked(rows: list[dict[str, Any]], size: int):
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def composite_hash(parts: dict[str, str]) -> str:
    blob = "|".join(f"{k}:{v}" for k, v in sorted(parts.items()))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def run(
    *,
    force: bool = False,
    layers: set[str] | None = None,
    official_seed_path: Path | None = None,
    spellbook_dir: Path | None = None,
    defillama_dir: Path | None = None,
    defillama_allowlist: set[str] | None = None,
) -> int:
    active = layers or {"p0"}
    sb = supabase_client()
    state = get_sync_state(sb)
    current = (state.get("source_hash") or "").strip()

    tmp: Path | None = None
    hash_parts: dict[str, str] = {}
    spell_labels: Path | None = None
    defi_projects: Path | None = None
    spell_commit: str | None = None
    defi_commit: str | None = None

    seed_path = official_seed_path or DEFAULT_OFFICIAL_SEED
    official_commit = file_sha256(seed_path)[:40]
    hash_parts["official"] = official_commit

    try:
        if "p1" in active:
            if spellbook_dir is not None:
                spell_labels = spellbook_dir / "labels" / "addresses"
                if not spell_labels.is_dir():
                    spell_labels = spellbook_dir
                spell_commit = "local"
            else:
                tmp = Path(tempfile.mkdtemp(prefix="walpulse-protocol-"))
                spell_root = tmp / "spellbook"
                sparse_clone(
                    SPELLBOOK_REPO,
                    spell_root,
                    (LABELS_ADDRESSES_REL,),
                    branch="main",
                )
                spell_labels = spell_root / LABELS_ADDRESSES_REL
                spell_commit = latest_github_commit(
                    SPELLBOOK_REPO, LABELS_ADDRESSES_REL, branch="main"
                )
            hash_parts["spellbook"] = spell_commit or "none"

        if "p2" in active:
            if defillama_dir is not None:
                defi_projects = defillama_dir / "projects"
                if not defi_projects.is_dir():
                    defi_projects = defillama_dir
                defi_commit = "local"
            else:
                if tmp is None:
                    tmp = Path(tempfile.mkdtemp(prefix="walpulse-protocol-"))
                defi_root = tmp / "defillama-adapters"
                sparse_clone(
                    DEFILLAMA_ADAPTERS_REPO,
                    defi_root,
                    ("projects",),
                    branch="main",
                )
                defi_projects = defi_root / "projects"
                defi_commit = latest_github_commit(
                    DEFILLAMA_ADAPTERS_REPO, "projects", branch="main"
                )
            hash_parts["defillama"] = defi_commit or "none"

        source_hash = composite_hash(hash_parts)
        if not force and current and current == source_hash:
            print("catalog unchanged — skip ingest", flush=True)
            return 0

        rows = collect_protocol_rows(
            official_seed_path=seed_path,
            official_commit=official_commit,
            spellbook_labels_dir=spell_labels,
            spellbook_commit=spell_commit,
            defillama_projects_dir=defi_projects,
            defillama_commit=defi_commit,
            defillama_allowlist=defillama_allowlist
            or set(DEFAULT_DEFILLAMA_ALLOWLIST),
            layers=active,
        )
        print(
            f"parsed {len(rows)} rows layers={sorted(active)}",
            flush=True,
        )
        if len(rows) < MIN_TOTAL_ROWS:
            raise SystemExit(
                f"row_count {len(rows)} below safety threshold {MIN_TOTAL_ROWS}"
            )

        sb.rpc("begin_protocol_addresses_ingest").execute()
        for batch in chunked(rows, APPEND_CHUNK):
            sb.rpc("append_protocol_addresses_ingest", {"p_rows": batch}).execute()
        result = (
            sb.rpc(
                "commit_protocol_addresses_ingest",
                {"p_source_hash": source_hash},
            )
            .execute()
            .data
        )
        print("commit:", result, flush=True)
        return 0
    finally:
        if tmp and tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync protocol_addresses catalog")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--layers",
        default="p0",
        help="Comma-separated: p0,p1,p2 (default p0)",
    )
    parser.add_argument("--official-seed", type=Path, default=None)
    parser.add_argument("--spellbook-dir", type=Path, default=None)
    parser.add_argument("--defillama-dir", type=Path, default=None)
    parser.add_argument(
        "--defillama-allowlist",
        default="",
        help="Comma-separated project slugs (P2); empty = default allowlist",
    )
    args = parser.parse_args(argv)
    layers = {x.strip().lower() for x in args.layers.split(",") if x.strip()}
    allow = (
        {x.strip().lower() for x in args.defillama_allowlist.split(",") if x.strip()}
        or None
    )
    return run(
        force=args.force,
        layers=layers,
        official_seed_path=args.official_seed,
        spellbook_dir=args.spellbook_dir,
        defillama_dir=args.defillama_dir,
        defillama_allowlist=allow,
    )


if __name__ == "__main__":
    sys.exit(main())
