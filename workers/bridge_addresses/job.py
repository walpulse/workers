"""Ingest bridge gateway contract addresses into Walpulse Supabase."""

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

from workers.bridge_addresses.parse import (
    ACROSS_ADDRESSES_URL,
    AXELAR_CONFIG_URL,
    CCIP_CHAINS_URL,
    DEFILLAMA_DATA_PATH,
    DEFILLAMA_REPO,
    HOP_ADAPTER_URL,
    STARGATE_API_URL,
    WORMHOLE_CONSTS_URL,
    collect_bridge_rows,
    load_json,
)

MIN_TOTAL_ROWS = 150
APPEND_CHUNK = 500
GITHUB_API = "https://api.github.com"
BRIDGES_CLONE_URL = f"https://github.com/{DEFILLAMA_REPO}.git"
SPARSE_PATHS = ("src/adapters", "src/data")


def _env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise SystemExit(f"missing required env: {name}")
    return value


def supabase_client() -> Client:
    return create_client(_env("SUPABASE_URL"), _env("SUPABASE_SERVICE_ROLE_KEY"))


def get_sync_state(sb: Client) -> dict[str, Any]:
    data = sb.rpc("get_bridge_addresses_sync_state").execute().data
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
        "User-Agent": "walpulse-workers-bridge-addresses",
    }
    token = (os.environ.get("GITHUB_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def latest_github_commit(repo: str, path: str, *, branch: str = "master") -> str:
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


def fetch_url(url: str, *, label: str) -> str:
    req = Request(url, headers={"User-Agent": "walpulse-workers-bridge-addresses"})
    try:
        with urlopen(req, timeout=120) as resp:
            return resp.read().decode("utf-8")
    except HTTPError as e:
        raise SystemExit(f"{label} download failed: HTTP {e.code}") from e
    except URLError as e:
        raise SystemExit(f"{label} download failed: {e}") from e


def fetch_json(url: str, *, label: str) -> dict[str, Any]:
    return json.loads(fetch_url(url, label=label))


def sparse_clone_bridges_server(dest: Path) -> Path:
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
            BRIDGES_CLONE_URL,
            str(dest),
        ]
    )
    run(["git", "sparse-checkout", "set", *SPARSE_PATHS], cwd=dest)
    return dest


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_source_hash(
    *,
    defillama_commit: str,
    stargate_body: str,
    wormhole_body: str,
    hop_body: str,
    ccip_body: str,
    across_body: str,
    axelar_body: str,
) -> str:
    parts = [
        f"defillama:{defillama_commit}",
        f"stargate:{sha256_text(stargate_body)}",
        f"wormhole:{sha256_text(wormhole_body)}",
        f"hop:{sha256_text(hop_body)}",
        f"ccip:{sha256_text(ccip_body)}",
        f"across:{sha256_text(across_body)}",
        f"axelar:{sha256_text(axelar_body)}",
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def chunked(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def replace_catalog(sb: Client, rows: list[dict[str, Any]], source_hash: str) -> dict[str, Any]:
    if len(rows) < MIN_TOTAL_ROWS:
        raise SystemExit(f"rows {len(rows)} below safety threshold {MIN_TOTAL_ROWS}")

    print(f"begin ingest: total={len(rows)} hash={source_hash[:12]}…", flush=True)
    sb.rpc("begin_bridge_addresses_ingest").execute()

    for i, batch in enumerate(chunked(rows, APPEND_CHUNK), start=1):
        n = sb.rpc("append_bridge_addresses_ingest", {"p_rows": batch}).execute().data
        print(f"  append chunk {i}: {n} rows", flush=True)

    result = sb.rpc(
        "commit_bridge_addresses_ingest", {"p_source_hash": source_hash}
    ).execute().data
    if isinstance(result, str):
        result = json.loads(result)
    print(f"commit ok: {result}", flush=True)
    return result if isinstance(result, dict) else {"raw": result}


def run(
    *,
    force: bool = False,
    defillama_dir: Path | None = None,
    stargate_json_path: Path | None = None,
    wormhole_consts_path: Path | None = None,
    hop_adapter_path: Path | None = None,
    ccip_json_path: Path | None = None,
    across_json_path: Path | None = None,
    axelar_json_path: Path | None = None,
) -> int:
    sb = supabase_client()
    state = get_sync_state(sb)
    current = (state.get("source_hash") or "").strip()

    tmp: Path | None = None
    try:
        if defillama_dir:
            repo_root = Path(defillama_dir)
            defillama_commit = sha256_text(
                (repo_root / DEFILLAMA_DATA_PATH).read_text(encoding="utf-8")
            )[:40]
        else:
            tmp = Path(tempfile.mkdtemp(prefix="walpulse-bridges-"))
            repo_root = sparse_clone_bridges_server(tmp / "bridges-server")
            defillama_commit = latest_github_commit(DEFILLAMA_REPO, DEFILLAMA_DATA_PATH)

        network_data = (repo_root / DEFILLAMA_DATA_PATH).read_text(encoding="utf-8")
        adapters_dir = repo_root / "src" / "adapters"

        if stargate_json_path:
            stargate_body = Path(stargate_json_path).read_text(encoding="utf-8")
            stargate_payload = json.loads(stargate_body)
        else:
            stargate_body = fetch_url(STARGATE_API_URL, label="Stargate metadata")
            stargate_payload = json.loads(stargate_body)

        if wormhole_consts_path:
            wormhole_body = Path(wormhole_consts_path).read_text(encoding="utf-8")
        else:
            wormhole_body = fetch_url(WORMHOLE_CONSTS_URL, label="Wormhole consts")

        if hop_adapter_path:
            hop_body = Path(hop_adapter_path).read_text(encoding="utf-8")
        else:
            hop_body = fetch_url(HOP_ADAPTER_URL, label="Hop adapter")

        if ccip_json_path:
            ccip_body = Path(ccip_json_path).read_text(encoding="utf-8")
            ccip_payload = json.loads(ccip_body)
        else:
            ccip_body = fetch_url(CCIP_CHAINS_URL, label="CCIP chains API")
            ccip_payload = json.loads(ccip_body)

        if across_json_path:
            across_body = Path(across_json_path).read_text(encoding="utf-8")
            across_payload = json.loads(across_body)
        else:
            across_body = fetch_url(ACROSS_ADDRESSES_URL, label="Across addresses")
            across_payload = json.loads(across_body)

        if axelar_json_path:
            axelar_body = Path(axelar_json_path).read_text(encoding="utf-8")
            axelar_payload = json.loads(axelar_body)
        else:
            axelar_body = fetch_url(AXELAR_CONFIG_URL, label="Axelar config")
            axelar_payload = json.loads(axelar_body)

        source_hash = compute_source_hash(
            defillama_commit=defillama_commit,
            stargate_body=stargate_body,
            wormhole_body=wormhole_body,
            hop_body=hop_body,
            ccip_body=ccip_body,
            across_body=across_body,
            axelar_body=axelar_body,
        )

        rows = collect_bridge_rows(
            defillama_adapters_dir=adapters_dir,
            bridge_network_data=network_data,
            stargate_payload=stargate_payload,
            wormhole_consts=wormhole_body,
            hop_adapter_text=hop_body,
            ccip_payload=ccip_payload,
            across_payload=across_payload,
            axelar_payload=axelar_payload,
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
    finally:
        if tmp and tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Re-ingest even if hash matches")
    parser.add_argument("--defillama-dir", type=Path, default=None, help="Local bridges-server root")
    parser.add_argument("--stargate-json-path", type=Path, default=None)
    parser.add_argument("--wormhole-consts-path", type=Path, default=None)
    parser.add_argument("--hop-adapter-path", type=Path, default=None)
    parser.add_argument("--ccip-json-path", type=Path, default=None)
    parser.add_argument("--across-json-path", type=Path, default=None)
    parser.add_argument("--axelar-json-path", type=Path, default=None)
    args = parser.parse_args(argv)
    return run(
        force=args.force,
        defillama_dir=args.defillama_dir,
        stargate_json_path=args.stargate_json_path,
        wormhole_consts_path=args.wormhole_consts_path,
        hop_adapter_path=args.hop_adapter_path,
        ccip_json_path=args.ccip_json_path,
        across_json_path=args.across_json_path,
        axelar_json_path=args.axelar_json_path,
    )


if __name__ == "__main__":
    sys.exit(main())
