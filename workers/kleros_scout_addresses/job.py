"""Ingest Kleros Scout address tags from Goldsky (Walpulse gtcr-subgraph) into Supabase."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from supabase import Client, create_client

from workers.kleros_scout_addresses.parse import (
    REGISTRIES,
    collect_kleros_scout_rows,
    compute_source_hash,
)

# Own indexer: gtcr-subgraph on Goldsky (Gnosis / xdai). Private endpoint.
DEFAULT_GOLDSKY_URL = (
    "https://api.goldsky.com/api/private/project_cmtdqgf2sj42x01w6f84b46m4"
    "/subgraphs/walpulse-scout-curate/1.0.0/gn"
)
# Legacy backends (opt-in via --source; not used in production).
THE_GRAPH_SUBGRAPH_ID = "9hHo5MpjpC1JqfD3BsgFnojGurXRHTrHWcUcZPPCo6m8"
ENVIO_GRAPHQL_URL = "https://indexer.hyperindex.xyz/1a2f51c/v1/graphql"
PAGE_SIZE = 1000
MIN_TOTAL_ROWS = 1000
APPEND_CHUNK = 500

LITEM_FIELDS = """
  itemID
  status
  key0
  key1
  key2
  key3
  latestRequestResolutionTime
"""


def _env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise SystemExit(f"missing required env: {name}")
    return value


def supabase_client() -> Client:
    return create_client(_env("SUPABASE_URL"), _env("SUPABASE_SERVICE_ROLE_KEY"))


def get_sync_state(sb: Client) -> dict[str, Any]:
    data = sb.rpc("get_kleros_scout_addresses_sync_state").execute().data
    if data is None:
        return {}
    if isinstance(data, str):
        return json.loads(data)
    if isinstance(data, dict):
        return data
    return {}


def graphql_request(
    url: str,
    query: str,
    *,
    label: str,
    bearer_token: str | None = None,
) -> dict[str, Any]:
    body = json.dumps({"query": query}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "walpulse-workers-kleros-scout",
    }
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    req = Request(url, data=body, headers=headers)
    try:
        with urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        raise RuntimeError(f"{label} GraphQL failed: HTTP {e.code}") from e
    except URLError as e:
        raise RuntimeError(f"{label} GraphQL failed: {e}") from e

    if payload.get("errors"):
        msg = payload["errors"][0].get("message", str(payload["errors"]))
        raise RuntimeError(f"{label} GraphQL error: {msg}")
    return payload


def _fetch_litems_graph_style(
    url: str,
    registry_address: str,
    *,
    label: str,
    bearer_token: str | None = None,
) -> list[dict[str, Any]]:
    """Paginate `litems` (The Graph / Goldsky schema)."""
    addr = registry_address.lower()
    items: list[dict[str, Any]] = []
    skip = 0
    while True:
        query = f"""
        {{
          litems(
            first: {PAGE_SIZE}
            skip: {skip}
            where: {{
              status_in: [Registered, ClearingRequested]
              registryAddress: "{addr}"
            }}
            orderBy: itemID
            orderDirection: asc
          ) {{
            {LITEM_FIELDS}
          }}
        }}
        """
        payload = graphql_request(
            url, query, label=label, bearer_token=bearer_token
        )
        batch = payload.get("data", {}).get("litems") or []
        if not batch:
            break
        items.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        skip += PAGE_SIZE
    return items


def fetch_registry_goldsky(
    api_key: str, registry_address: str, graphql_url: str
) -> list[dict[str, Any]]:
    return _fetch_litems_graph_style(
        graphql_url,
        registry_address,
        label="Goldsky",
        bearer_token=api_key,
    )


def fetch_registry_graph(api_key: str, registry_address: str) -> list[dict[str, Any]]:
    url = f"https://gateway.thegraph.com/api/{api_key}/subgraphs/id/{THE_GRAPH_SUBGRAPH_ID}"
    return _fetch_litems_graph_style(url, registry_address, label="The Graph")


def fetch_registry_envio(registry_address: str) -> list[dict[str, Any]]:
    addr = registry_address.lower()
    items: list[dict[str, Any]] = []
    offset = 0
    while True:
        query = f"""
        {{
          LItem(
            limit: {PAGE_SIZE}
            offset: {offset}
            where: {{
              status: {{ _in: ["Registered", "ClearingRequested"] }}
              registryAddress: {{ _eq: "{addr}" }}
            }}
          ) {{
            {LITEM_FIELDS}
          }}
        }}
        """
        payload = graphql_request(ENVIO_GRAPHQL_URL, query, label="Envio")
        batch = payload.get("data", {}).get("LItem") or []
        if not batch:
            break
        items.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return items


def fetch_all_registries(
    *,
    source: str,
    api_key: str | None,
    goldsky_url: str,
) -> dict[str, list[dict[str, Any]]]:
    items_by_registry: dict[str, list[dict[str, Any]]] = {}
    for registry_address, registry_name in REGISTRIES.items():
        print(f"fetch {registry_name} ({registry_address}) via {source}…", flush=True)
        if source == "goldsky":
            if not api_key:
                raise SystemExit("missing required env: GOLDSKY_API_KEY")
            raw = fetch_registry_goldsky(api_key, registry_address, goldsky_url)
        elif source == "graph":
            if not api_key:
                raise SystemExit("missing required env: THE_GRAPH_KEY")
            raw = fetch_registry_graph(api_key, registry_address)
        else:
            raw = fetch_registry_envio(registry_address)
        print(f"  {len(raw)} raw items", flush=True)
        items_by_registry[registry_name] = raw
    return items_by_registry


def load_fixture(path: Path) -> dict[str, list[dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"fixture must be a JSON object: {path}")
    return {str(k): list(v) for k, v in data.items()}


def chunked(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def replace_catalog(
    sb: Client,
    rows: list[dict[str, Any]],
    source_hash: str,
) -> dict[str, Any]:
    if len(rows) < MIN_TOTAL_ROWS:
        raise SystemExit(f"rows {len(rows)} below safety threshold {MIN_TOTAL_ROWS}")

    print(
        f"begin ingest: total={len(rows)} hash={source_hash[:12]}…",
        flush=True,
    )
    sb.rpc("begin_kleros_scout_addresses_ingest").execute()

    for i, batch in enumerate(chunked(rows, APPEND_CHUNK), start=1):
        n = sb.rpc("append_kleros_scout_addresses_ingest", {"p_rows": batch}).execute().data
        print(f"  append chunk {i}: {n} rows", flush=True)

    result = sb.rpc(
        "commit_kleros_scout_addresses_ingest",
        {"p_source_hash": source_hash},
    ).execute().data
    if isinstance(result, str):
        result = json.loads(result)
    print(f"commit ok: {result}", flush=True)
    return result if isinstance(result, dict) else {"raw": result}


def run(
    *,
    force: bool = False,
    fixture_json: Path | None = None,
    source: str = "goldsky",
) -> int:
    sb = supabase_client()
    state = get_sync_state(sb)
    current = (state.get("source_hash") or "").strip()

    goldsky_url = (
        (os.environ.get("GOLDSKY_GRAPHQL_URL") or "").strip() or DEFAULT_GOLDSKY_URL
    )
    if source == "goldsky":
        api_key = (os.environ.get("GOLDSKY_API_KEY") or "").strip() or None
    elif source == "graph":
        api_key = (os.environ.get("THE_GRAPH_KEY") or "").strip() or None
    else:
        api_key = None

    if fixture_json:
        print(f"loading fixture {fixture_json}", flush=True)
        items_by_registry = load_fixture(fixture_json)
        fetch_source = "fixture"
    else:
        fetch_source = source
        items_by_registry = fetch_all_registries(
            source=source,
            api_key=api_key,
            goldsky_url=goldsky_url,
        )

    source_hash = compute_source_hash(items_by_registry)
    print(f"source hash: {source_hash} (via {fetch_source})", flush=True)
    print(f"walpulse sync state: {state or '(empty)'}", flush=True)

    if not force and current and current == source_hash:
        print("catalog unchanged — skip ingest", flush=True)
        return 0

    if force and current == source_hash:
        print("force=true — re-ingest same hash", flush=True)

    rows = collect_kleros_scout_rows(items_by_registry)
    print(f"parsed rows: {len(rows)}", flush=True)
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
        "--fixture-json",
        type=Path,
        default=None,
        help="Local JSON with items by registry (skip network fetch)",
    )
    parser.add_argument(
        "--source",
        choices=("goldsky", "graph", "envio"),
        default="goldsky",
        help="GraphQL backend (default: goldsky private Walpulse subgraph)",
    )
    args = parser.parse_args(argv)
    return run(force=args.force, fixture_json=args.fixture_json, source=args.source)


if __name__ == "__main__":
    sys.exit(main())
