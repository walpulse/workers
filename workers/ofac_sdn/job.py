"""Ingest OFAC SDN Advanced digital currency addresses into Walpulse Supabase."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from supabase import Client, create_client

from workers.ofac_sdn.parse import collect_ofac_rows, load_reference_data

SDN_ADVANCED_ZIP_URL = (
    "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ADVANCED.ZIP"
)
MIN_TOTAL_ROWS = 30
APPEND_CHUNK = 500


def _env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise SystemExit(f"missing required env: {name}")
    return value


def supabase_client() -> Client:
    return create_client(_env("SUPABASE_URL"), _env("SUPABASE_SERVICE_ROLE_KEY"))


def get_sync_state(sb: Client) -> dict[str, Any]:
    data = sb.rpc("get_ofac_sdn_addresses_sync_state").execute().data
    if data is None:
        return {}
    if isinstance(data, str):
        return json.loads(data)
    if isinstance(data, dict):
        return data
    return {}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_sdn_advanced_zip(dest_zip: Path) -> None:
    headers = {"User-Agent": "walpulse-workers-ofac-sdn"}
    req = Request(SDN_ADVANCED_ZIP_URL, headers=headers)
    try:
        with urlopen(req, timeout=300) as resp:
            data = resp.read()
    except HTTPError as e:
        raise SystemExit(f"OFAC download failed: HTTP {e.code}") from e
    except URLError as e:
        raise SystemExit(f"OFAC download failed: {e}") from e
    dest_zip.write_bytes(data)


def extract_xml_from_zip(zip_path: Path, dest_xml: Path) -> Path:
    with zipfile.ZipFile(zip_path) as zf:
        inner = next(n for n in zf.namelist() if n.lower().endswith(".xml"))
        dest_xml.write_bytes(zf.read(inner))
    return dest_xml


def chunked(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def replace_catalog(
    sb: Client,
    rows: list[dict[str, Any]],
    source_hash: str,
    list_updated_at: date | None,
) -> dict[str, Any]:
    if len(rows) < MIN_TOTAL_ROWS:
        raise SystemExit(f"rows {len(rows)} below safety threshold {MIN_TOTAL_ROWS}")

    evm_n = sum(1 for r in rows if r["blockchain"] == "evm")
    print(
        f"begin ingest: total={len(rows)} evm={evm_n} hash={source_hash[:12]}…",
        flush=True,
    )
    sb.rpc("begin_ofac_sdn_addresses_ingest").execute()

    for i, batch in enumerate(chunked(rows, APPEND_CHUNK), start=1):
        n = sb.rpc("append_ofac_sdn_addresses_ingest", {"p_rows": batch}).execute().data
        print(f"  append chunk {i}: {n} rows", flush=True)

    payload: dict[str, Any] = {"p_source_hash": source_hash}
    if list_updated_at is not None:
        payload["p_list_updated_at"] = list_updated_at.isoformat()

    result = sb.rpc("commit_ofac_sdn_addresses_ingest", payload).execute().data
    if isinstance(result, str):
        result = json.loads(result)
    print(f"commit ok: {result}", flush=True)
    return result if isinstance(result, dict) else {"raw": result}


def run(*, force: bool = False, xml_path: Path | None = None) -> int:
    sb = supabase_client()
    state = get_sync_state(sb)
    current = (state.get("source_hash") or "").strip()

    tmp: Path | None = None
    zip_path: Path | None = None
    try:
        if xml_path:
            xml_file = Path(xml_path)
            if not xml_file.is_file():
                raise SystemExit(f"--xml-path not a file: {xml_file}")
            source_hash = sha256_file(xml_file)
        else:
            tmp = Path(tempfile.mkdtemp(prefix="ofac-sdn-"))
            zip_path = tmp / "SDN_ADVANCED.ZIP"
            xml_file = tmp / "SDN_ADVANCED.XML"
            print(f"downloading {SDN_ADVANCED_ZIP_URL}", flush=True)
            download_sdn_advanced_zip(zip_path)
            source_hash = sha256_file(zip_path)
            extract_xml_from_zip(zip_path, xml_file)

        print(f"source hash: {source_hash}", flush=True)
        print(f"walpulse sync state: {state or '(empty)'}", flush=True)

        if not force and current and current == source_hash:
            print("catalog unchanged — skip ingest", flush=True)
            return 0

        if force and current == source_hash:
            print("force=true — re-ingest same hash", flush=True)

        print("loading reference data…", flush=True)
        feature_types, profile_programs, list_updated_at = load_reference_data(xml_file)
        print(
            f"reference: {len(feature_types)} digital-currency feature types, "
            f"{len(profile_programs)} profiles with programs, "
            f"list_updated_at={list_updated_at}",
            flush=True,
        )

        rows, list_updated_at = collect_ofac_rows(
            xml_file,
            feature_types=feature_types,
            profile_programs=profile_programs,
            list_updated_at=list_updated_at,
        )
        replace_catalog(sb, rows, source_hash, list_updated_at)
    finally:
        if tmp and tmp.exists():
            for p in tmp.iterdir():
                if p.is_file():
                    p.unlink(missing_ok=True)
            tmp.rmdir()

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest even if source_hash matches stored sync state",
    )
    parser.add_argument(
        "--xml-path",
        type=Path,
        default=None,
        help="Local SDN_ADVANCED.XML (skip download; hash computed from file bytes)",
    )
    args = parser.parse_args(argv)
    return run(force=args.force, xml_path=args.xml_path)


if __name__ == "__main__":
    sys.exit(main())
