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
    CYCLONE_DOCS_FALLBACK_URL,
    CYCLONE_DOCS_URL,
    L2BEAT_PROJECT_SLUGS,
    L2BEAT_RAW_BASE,
    RAILGUN_CHAINS,
    RAILGUN_DEPLOYMENTS_PATH,
    RAILGUN_DEPLOYMENTS_RAW_BASE,
    RAILGUN_DEPLOYMENTS_REPO,
    TORNADO_DOCS_PATH,
    TORNADO_DOCS_REPO,
    TORNADO_DOCS_URL,
    collect_mixer_rows,
    load_l2beat_discovery,
)

MIN_TOTAL_ROWS = 20
APPEND_CHUNK = 500
GITHUB_API = "https://api.github.com"
DEFAULT_TYPHOON_SEED = Path(__file__).resolve().parent / "data" / "typhoon_seed.json"


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


def _http_get_text(url: str, *, timeout: int = 120) -> str:
    req = Request(url, headers={"User-Agent": "walpulse-workers-mixer-addresses"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def fetch_tornado_markdown() -> str:
    try:
        return _http_get_text(TORNADO_DOCS_URL)
    except HTTPError as e:
        raise SystemExit(f"Tornado docs download failed: HTTP {e.code}") from e
    except URLError as e:
        raise SystemExit(f"Tornado docs download failed: {e}") from e


def fetch_l2beat_discoveries() -> dict[str, dict[str, Any]]:
    discoveries: dict[str, dict[str, Any]] = {}
    for slug in L2BEAT_PROJECT_SLUGS:
        if slug == "strk20":
            discoveries[slug] = {}
            continue
        url = f"{L2BEAT_RAW_BASE}/{slug}/discovered.json"
        try:
            discoveries[slug] = json.loads(_http_get_text(url))
        except HTTPError as e:
            if e.code == 404:
                print(f"warning: L2BEAT discovery missing for {slug} — skip", flush=True)
                continue
            raise SystemExit(f"L2BEAT download failed for {slug}: HTTP {e.code}") from e
        except URLError as e:
            raise SystemExit(f"L2BEAT download failed for {slug}: {e}") from e
    return discoveries


def fetch_railgun_chain_sources() -> dict[str, str]:
    sources: dict[str, str] = {}
    for chain in RAILGUN_CHAINS:
        url = f"{RAILGUN_DEPLOYMENTS_RAW_BASE}/{chain}.ts"
        try:
            sources[chain] = _http_get_text(url)
        except HTTPError as e:
            if e.code == 404:
                print(f"warning: Railgun deployments missing for {chain} — skip", flush=True)
                continue
            raise SystemExit(f"Railgun download failed for {chain}: HTTP {e.code}") from e
        except URLError as e:
            raise SystemExit(f"Railgun download failed for {chain}: {e}") from e
    return sources


def fetch_cyclone_markdown() -> str:
    for url in (CYCLONE_DOCS_URL, CYCLONE_DOCS_FALLBACK_URL):
        try:
            return _http_get_text(url)
        except HTTPError:
            continue
        except URLError:
            continue
    raise SystemExit("Cyclone docs download failed for all candidate URLs")


def compute_source_hash(
    tornado_commit: str,
    l2beat_discoveries: dict[str, dict[str, Any]],
    *,
    railgun_commit: str = "",
    cyclone_hash: str = "",
    typhoon_hash: str = "",
) -> str:
    parts = [f"tornado-docs:{tornado_commit}"]
    for slug in sorted(l2beat_discoveries):
        disc = l2beat_discoveries[slug]
        if slug == "strk20":
            parts.append(f"{slug}:static")
        else:
            parts.append(f"{slug}:{disc.get('configHash', '')}")
    if railgun_commit:
        parts.append(f"railgun-deployments:{railgun_commit}")
    if cyclone_hash:
        parts.append(f"cyclone-docs:{cyclone_hash}")
    if typhoon_hash:
        parts.append(f"typhoon-seed:{typhoon_hash}")
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
    cyclone_md_path: Path | None = None,
    railgun_dir: Path | None = None,
    typhoon_seed_path: Path | None = None,
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
        l2beat_discoveries: dict[str, dict[str, Any]] = {}
        base = Path(l2beat_dir)
        for slug in L2BEAT_PROJECT_SLUGS:
            if slug == "strk20":
                l2beat_discoveries[slug] = {}
                continue
            path = base / slug / "discovered.json"
            if path.is_file():
                l2beat_discoveries[slug] = load_l2beat_discovery(path)
    else:
        l2beat_discoveries = fetch_l2beat_discoveries()

    if railgun_dir:
        railgun_sources = {}
        for chain in RAILGUN_CHAINS:
            path = Path(railgun_dir) / f"{chain}.ts"
            if path.is_file():
                railgun_sources[chain] = path.read_text(encoding="utf-8")
        railgun_commit = hashlib.sha256(
            "".join(railgun_sources[c] for c in sorted(railgun_sources)).encode()
        ).hexdigest()[:40]
    else:
        railgun_sources = fetch_railgun_chain_sources()
        railgun_commit = latest_github_commit(
            RAILGUN_DEPLOYMENTS_REPO,
            RAILGUN_DEPLOYMENTS_PATH,
            branch="master",
        )

    if cyclone_md_path:
        cyclone_md = Path(cyclone_md_path).read_text(encoding="utf-8")
    else:
        cyclone_md = fetch_cyclone_markdown()
    cyclone_hash = hashlib.sha256(cyclone_md.encode("utf-8")).hexdigest()[:40]

    seed_path = typhoon_seed_path or DEFAULT_TYPHOON_SEED
    typhoon_hash = ""
    if seed_path.is_file():
        typhoon_hash = hashlib.sha256(
            seed_path.read_bytes()
        ).hexdigest()[:40]

    source_hash = compute_source_hash(
        tornado_commit,
        l2beat_discoveries,
        railgun_commit=railgun_commit,
        cyclone_hash=cyclone_hash,
        typhoon_hash=typhoon_hash,
    )
    rows = collect_mixer_rows(
        tornado_markdown=markdown,
        l2beat_discoveries=l2beat_discoveries,
        railgun_chain_sources=railgun_sources,
        cyclone_markdown=cyclone_md,
        typhoon_seed_path=seed_path if seed_path.is_file() else None,
    )

    print(f"source hash: {source_hash}", flush=True)
    print(f"walpulse sync state: {state or '(empty)'}", flush=True)
    print(f"parsed rows: {len(rows)}", flush=True)
    by_proto: dict[str, int] = {}
    for r in rows:
        by_proto[r["protocol"]] = by_proto.get(r["protocol"], 0) + 1
    print(f"by protocol: {by_proto}", flush=True)

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
    parser.add_argument(
        "--cyclone-md-path",
        type=Path,
        default=None,
        help="Local Cyclone deployment markdown (skip download)",
    )
    parser.add_argument(
        "--railgun-dir",
        type=Path,
        default=None,
        help="Local Railgun deployments chain TS dir",
    )
    parser.add_argument(
        "--typhoon-seed-path",
        type=Path,
        default=None,
        help="Typhoon allowlist JSON (default: data/typhoon_seed.json)",
    )
    args = parser.parse_args(argv)
    return run(
        force=args.force,
        tornado_md_path=args.tornado_md_path,
        l2beat_dir=args.l2beat_dir,
        cyclone_md_path=args.cyclone_md_path,
        railgun_dir=args.railgun_dir,
        typhoon_seed_path=args.typhoon_seed_path,
    )


if __name__ == "__main__":
    sys.exit(main())
