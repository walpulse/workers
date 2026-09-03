"""Ingest Sourcify Parquet export v2 into Walpulse Supabase (incremental ETag manifest)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pyarrow.parquet as pq
from postgrest.exceptions import APIError
from supabase import Client, create_client

from workers.sourcify_verified.export_list import ExportFile, list_export_files
from workers.sourcify_verified.parse import (
    INGEST_ORDER,
    TABLE_DEPLOYMENTS,
    TABLE_VERIFIED,
    build_manifest_index,
    is_file_pending,
    parse_batch,
)

APPEND_CHUNK = 500
DEFAULT_MAX_RUNTIME_SECONDS = 19_800  # 5.5 h
RUNTIME_MARGIN_SECONDS = 120
UPSERT_MAX_ATTEMPTS = 3
UPSERT_RETRY_BACKOFF_SECONDS = (1.0, 2.0, 4.0)
USER_AGENT = "walpulse-workers-sourcify-verified"

TABLE_RPC = {
    TABLE_DEPLOYMENTS: "upsert_sourcify_deployments",
    TABLE_VERIFIED: "upsert_sourcify_verified_from_deployments",
}


def _env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise SystemExit(f"missing required env: {name}")
    return value


def supabase_client() -> Client:
    return create_client(_env("SUPABASE_URL"), _env("SUPABASE_SERVICE_ROLE_KEY"))


def get_sync_state(sb: Client) -> dict[str, Any]:
    data = sb.rpc("get_sourcify_verified_sync_state").execute().data
    if data is None:
        return {}
    if isinstance(data, str):
        return json.loads(data)
    if isinstance(data, dict):
        return data
    return {}


def load_manifest(sb: Client) -> dict[str, dict[str, str]]:
    data = sb.rpc("get_sourcify_export_files").execute().data
    if data is None:
        rows: list[dict[str, Any]] = []
    elif isinstance(data, str):
        rows = json.loads(data)
    elif isinstance(data, list):
        rows = data
    else:
        rows = []
    return build_manifest_index(rows)


def chunked(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def download_file(url: str, dest: Path) -> None:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=600) as resp, dest.open("wb") as out:
            while True:
                block = resp.read(1024 * 1024)
                if not block:
                    break
                out.write(block)
    except HTTPError as e:
        raise RuntimeError(f"download failed: HTTP {e.code} {url}") from e
    except URLError as e:
        raise RuntimeError(f"download failed: {e} {url}") from e


def _is_statement_timeout(exc: BaseException) -> bool:
    if isinstance(exc, APIError):
        code = getattr(exc, "code", None) or (exc.args[0].get("code") if exc.args else None)
        if code == "57014":
            return True
        message = str(exc).lower()
        return "statement timeout" in message or "57014" in message
    return False


def upsert_batches(sb: Client, rpc_name: str, rows: list[dict[str, Any]]) -> int:
    total = 0
    for batch in chunked(rows, APPEND_CHUNK):
        last_exc: BaseException | None = None
        for attempt in range(1, UPSERT_MAX_ATTEMPTS + 1):
            try:
                n = sb.rpc(rpc_name, {"p_rows": batch}).execute().data
                total += int(n or 0)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                if not _is_statement_timeout(exc) or attempt >= UPSERT_MAX_ATTEMPTS:
                    raise
                delay = UPSERT_RETRY_BACKOFF_SECONDS[min(attempt - 1, len(UPSERT_RETRY_BACKOFF_SECONDS) - 1)]
                print(
                    f"  upsert {rpc_name} statement timeout (attempt {attempt}/{UPSERT_MAX_ATTEMPTS}); "
                    f"retry in {delay:.0f}s",
                    flush=True,
                )
                time.sleep(delay)
        if last_exc is not None:
            raise last_exc
    return total


def record_export_file(
    sb: Client,
    export_file: ExportFile,
    *,
    row_count: int,
) -> None:
    last_modified = export_file.last_modified
    sb.rpc(
        "record_sourcify_export_file",
        {
            "p_table": export_file.table_name,
            "p_file_key": export_file.file_key,
            "p_etag": export_file.etag,
            "p_file_size": export_file.size,
            "p_last_modified": last_modified,
            "p_row_count": row_count,
        },
    ).execute()


def update_sync_run(sb: Client, status: str, files_processed: int) -> dict[str, Any]:
    data = sb.rpc(
        "update_sourcify_verified_sync_run",
        {"p_status": status, "p_files_processed": files_processed},
    ).execute().data
    if isinstance(data, str):
        return json.loads(data)
    if isinstance(data, dict):
        return data
    return {}


def build_pending_queue(
    table_names: tuple[str, ...],
    manifest: dict[str, dict[str, str]],
    *,
    force: bool,
    local_parquet_dir: Path | None,
) -> list[ExportFile]:
    pending: list[ExportFile] = []
    for table_name in table_names:
        if local_parquet_dir is not None:
            table_dir = local_parquet_dir / table_name
            if not table_dir.is_dir():
                continue
            for path in sorted(table_dir.glob("*.parquet")):
                key = f"v2/{table_name}/{path.name}"
                if not is_file_pending(
                    "local",
                    manifest,
                    table_name=table_name,
                    file_key=key,
                    force=force,
                ):
                    continue
                pending.append(
                    ExportFile(
                        table_name=table_name,
                        file_key=key,
                        etag="local",
                        size=path.stat().st_size,
                        last_modified=None,
                    )
                )
            continue

        remote_files = list_export_files(table_name)
        for export_file in remote_files:
            if is_file_pending(
                export_file.etag,
                manifest,
                table_name=table_name,
                file_key=export_file.file_key,
                force=force,
            ):
                pending.append(export_file)
    return pending


def ingest_parquet_file(
    sb: Client,
    export_file: ExportFile,
    *,
    local_parquet_dir: Path | None,
) -> tuple[int, int]:
    """Returns (parquet_rows_read, upserted_rows)."""
    if local_parquet_dir is not None:
        parquet_path = local_parquet_dir / export_file.table_name / Path(export_file.file_key).name
        if not parquet_path.is_file():
            raise RuntimeError(f"local parquet missing: {parquet_path}")
        reader_ctx = pq.ParquetFile(parquet_path)
        cleanup: Path | None = None
    else:
        tmp = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()
        try:
            download_file(export_file.download_url, tmp_path)
            reader_ctx = pq.ParquetFile(tmp_path)
            cleanup = tmp_path
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise

    rpc_name = TABLE_RPC[export_file.table_name]
    row_count = 0
    upserted = 0
    try:
        for batch in reader_ctx.iter_batches(batch_size=APPEND_CHUNK):
            dict_rows = batch.to_pylist()
            parsed = parse_batch(export_file.table_name, dict_rows)
            if parsed:
                upserted += upsert_batches(sb, rpc_name, parsed)
            row_count += len(dict_rows)
    finally:
        if cleanup is not None:
            cleanup.unlink(missing_ok=True)

    record_export_file(sb, export_file, row_count=row_count)
    return row_count, upserted


def run(
    *,
    force: bool = False,
    table_filter: str | None = None,
    max_runtime_seconds: int = DEFAULT_MAX_RUNTIME_SECONDS,
    local_parquet_dir: Path | None = None,
) -> int:
    started = time.monotonic()
    deadline = started + max(60, max_runtime_seconds)

    table_names: tuple[str, ...]
    if table_filter:
        if table_filter not in INGEST_ORDER:
            raise SystemExit(f"unknown table: {table_filter}")
        table_names = (table_filter,)
    else:
        table_names = INGEST_ORDER

    sb = supabase_client()
    manifest = load_manifest(sb)
    pending = build_pending_queue(
        table_names,
        manifest,
        force=force,
        local_parquet_dir=local_parquet_dir,
    )

    if not pending:
        summary = update_sync_run(sb, "catch_up_complete", 0)
        print("catch_up_complete — no pending export files", flush=True)
        print(json.dumps(summary, default=str), flush=True)
        return 0

    files_processed = 0
    try:
        for export_file in pending:
            remaining = deadline - time.monotonic()
            if remaining <= RUNTIME_MARGIN_SECONDS:
                summary = update_sync_run(sb, "partial_progress", files_processed)
                print("partial_progress — runtime budget exhausted", flush=True)
                print(json.dumps(summary, default=str), flush=True)
                return 0

            print(
                f"ingesting {export_file.table_name} {export_file.file_key} "
                f"({export_file.size} bytes)",
                flush=True,
            )
            rows, upserted = ingest_parquet_file(
                sb, export_file, local_parquet_dir=local_parquet_dir
            )
            files_processed += 1
            print(
                f"  done parquet_rows={rows} upserted={upserted}",
                flush=True,
            )
            if export_file.table_name == TABLE_VERIFIED and rows > 0 and upserted == 0:
                print(
                    "  warning: verified upserted=0 (INNER JOIN miss — deployments incomplete?)",
                    flush=True,
                )

        summary = update_sync_run(sb, "catch_up_complete", files_processed)
        print("catch_up_complete", flush=True)
        print(json.dumps(summary, default=str), flush=True)
        return 0
    except Exception as exc:
        try:
            update_sync_run(sb, "error", files_processed)
        except Exception as sync_exc:
            print(f"update_sync_run failed after error: {sync_exc}", flush=True)
        raise exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Sourcify verified contracts export")
    parser.add_argument("--force", action="store_true", help="Re-ingest even if ETag matches")
    parser.add_argument(
        "--table",
        choices=list(INGEST_ORDER),
        help="Limit ingest to one export table",
    )
    parser.add_argument(
        "--max-runtime-seconds",
        type=int,
        default=DEFAULT_MAX_RUNTIME_SECONDS,
        help=f"Max work budget (default {DEFAULT_MAX_RUNTIME_SECONDS})",
    )
    parser.add_argument(
        "--local-parquet-dir",
        type=Path,
        help="Local directory with v2/<table>/*.parquet fixtures",
    )
    args = parser.parse_args()
    return run(
        force=args.force,
        table_filter=args.table,
        max_runtime_seconds=args.max_runtime_seconds,
        local_parquet_dir=args.local_parquet_dir,
    )


if __name__ == "__main__":
    sys.exit(main())
