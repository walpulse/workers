"""Ingest mixer/privacy contract addresses into Walpulse Supabase."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from supabase import Client, create_client

from workers.mixer_addresses.parse import (
    L2BEAT_PROJECT_SLUGS,
    L2BEAT_RAW_BASE,
    TORNADO_DOCS_PATH,
    TORNADO_DOCS_REPO,
    TORNADO_DOCS_URL,
    collect_mixer_rows,
    load_l2beat_discovery,
)

MIN_TOTAL_ROWS = 20
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
    data = sb.rpc("get_mixer_addresses_sync_state").execute().data
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
        "User-Agent": "walpulse-workers-mixer-addresses",
    }
    token = (os.environ.get("GITHUB_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def latest_github_commit(repo: str, path: str, *, branch: str = "en") -> str:
    url = (
        f"{GITHUB_API}/repos/{repo}/commits"
        f"?path={quote(path)}&per_page=1&sha={quote(branch)}"
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


def fetch_tornado_markdown() -> str:
    req = Request(TORNADO_DOCS_URL, headers={"User-Agent": "walpulse-workers-mixer-addresses"})
    try:
        with urlopen(req, timeout=120) as resp:
            return resp.read().decode("utf-8")
    except HTTPError as e:
        raise SystemExit(f"Tornado docs download failed: HTTP {e.code}") from e
    except URLError as e:
        raise SystemExit(f"Tornado docs download failed: {e}") from e


def fetch_l2beat_discoveries() -> dict[str, dict[str, Any]]:
    discoveries: dict[str, dict[str, Any]] = {}
    headers = {"User-Agent": "walpulse-workers-mixer-addresses"}
    for slug in L2BEAT_PROJECT_SLUGS:
        if slug == "strk20":
            discoveries[slug] = {}
            continue
        url = f"{L2BEAT_RAW_BASE}/{slug}/discovered.json"
        req = Request(url, headers=headers)
        try:
            with urlopen(req, timeout=120) as resp:
                discoveries[slug] = json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 404:
                print(f"warning: L2BEAT discovery missing for {slug} — skip", flush=True)
                continue
            raise SystemExit(f"L2BEAT download failed for {slug}: HTTP {e.code}") from e
        except URLError as e:
            raise SystemExit(f"L2BEAT download failed for {slug}: {e}") from e
    return discoveries


def compute_source_hash(
    tornado_commit: str,
    l2beat_discoveries: dict[str, dict[str, Any]],
) -> str:
    parts = [f"tornado-docs:{tornado_commit}"]
    for slug in sorted(l2beat_discoveries):
        disc = l2beat_discoveries[slug]
        if slug == "strk20":
            parts.append(f"{slug}:static")
        else:
            parts.append(f"{slug}:{disc.get('configHash', '')}")
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def chunked(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def replace_catalog(sb: Client, rows: list[dict[str, Any]], source_hash: str) -> dict[str, Any]:
    if len(rows) < MIN_TOTAL_ROWS:
        raise SystemExit(f"rows {len(rows)} below safety threshold {MIN_TOTAL_ROWS}")

    print(
        f"begin ingest: total={len(rows)} hash={source_hash[:12]}…",
        flush=True,
    )
    sb.rpc("begin_mixer_addresses_ingest").execute()

    for i, batch in enumerate(chunked(rows, APPEND_CHUNK), start=1):
        n = sb.rpc("append_mixer_addresses_ingest", {"p_rows": batch}).execute().data
        print(f"  append chunk {i}: {n} rows", flush=True)

    result = sb.rpc(
        "commit_mixer_addresses_ingest", {"p_source_hash": source_hash}
    ).execute().data
    if isinstance(result, str):
        result = json.loads(result)
    print(f"commit ok: {result}", flush=True)
    return result if isinstance(result, dict) else {"raw": result}


def run(
    *,
    force: bool = False,
    tornado_md_path: Path | None = None,
    l2beat_dir: Path | None = None,
) -> int:
    sb = supabase_client()
    state = get_sync_state(sb)
    current = (state.get("source_hash") or "").strip()

    if tornado_md_path:
        markdown = Path(tornado_md_path).read_text(encoding="utf-8")
        tornado_commit = hashlib.sha256(markdown.encode("utf-8")).hexdigest()[:40]
    else:
        tornado_commit = latest_github_commit(TORNADO_DOCS_REPO, TORNADO_DOCS_PATH)
        markdown = fetch_tornado_markdown()

    if l2beat_dir:
        l2beat_discoveries = {}
        base = Path(l2beat_dir)
        for slug in L2BEAT_PROJECT_SLUGS:
            if slug == "strk20":
                l2beat_discoveries[slug] = {}
                continue
            path = base / slug / "discovered.json"
            if path.is_file():
                l2beat_discoveries[slug] = load_l2beat_discovery(path)
        source_hash = compute_source_hash(tornado_commit, l2beat_discoveries)
        rows = collect_mixer_rows(
            tornado_markdown=markdown,
            l2beat_discoveries=l2beat_discoveries,
        )
    else:
        l2beat_discoveries = fetch_l2beat_discoveries()
        source_hash = compute_source_hash(tornado_commit, l2beat_discoveries)
        rows = collect_mixer_rows(
            tornado_markdown=markdown,
            l2beat_discoveries=l2beat_discoveries,
        )

    print(f"source hash: {source_hash}", flush=True)
    print(f"walpulse sync state: {state or '(empty)'}", flush=True)
    print(f"parsed rows: {len(rows)}", flush=True)

    if not force and current and current == source_hash:
        print("catalog unchanged — skip ingest", flush=True)
        return 0

    if force and current == source_hash:
        print("force=true — re-ingest same hash", flush=True)

    replace_catalog(sb, rows, source_hash)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest even if source_hash matches stored sync state",
    )
    parser.add_argument(
        "--tornado-md-path",
        type=Path,
        default=None,
        help="Local tornado-cash-smart-contracts.md (skip download)",
    )
    parser.add_argument(
        "--l2beat-dir",
        type=Path,
        default=None,
        help="Local L2BEAT projects dir (packages/config/src/projects)",
    )
    args = parser.parse_args(argv)
    return run(
        force=args.force,
        tornado_md_path=args.tornado_md_path,
        l2beat_dir=args.l2beat_dir,
    )


if __name__ == "__main__":
    sys.exit(main())
