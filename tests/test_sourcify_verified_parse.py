"""Tests for workers.sourcify_verified.parse and export manifest helpers."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from workers.sourcify_verified.parse import (
    TABLE_DEPLOYMENTS,
    TABLE_VERIFIED,
    build_manifest_index,
    is_file_pending,
    normalize_address,
    parse_batch,
    parse_deployment_row,
    parse_verified_row,
)


def test_normalize_address_hex_and_bytes():
    assert normalize_address(b"\xde\xad") is None  # too short
    addr = "0x" + "ab" * 20
    assert normalize_address(addr) == addr
    assert normalize_address(addr.upper()) == addr
    raw = bytes.fromhex("ab" * 20)
    assert normalize_address(raw) == addr


def test_parse_deployment_row():
    row = {
        "id": "dep-1",
        "chain_id": 1,
        "address": bytes.fromhex("abcd" * 10),
        "contract_id": "ctr-1",
    }
    parsed = parse_deployment_row(row)
    assert parsed is not None
    assert parsed["deployment_id"] == "dep-1"
    assert parsed["chain_id"] == 1
    assert parsed["address"] == "0x" + "abcd" * 10


def test_parse_verified_row():
    row = {
        "deployment_id": "dep-1",
        "compilation_id": "cmp-1",
        "creation_match": True,
        "runtime_match": False,
        "creation_metadata_match": True,
        "runtime_metadata_match": False,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-02T00:00:00",
    }
    parsed = parse_verified_row(row)
    assert parsed is not None
    assert parsed["deployment_id"] == "dep-1"
    assert parsed["creation_match"] is True
    assert parsed["runtime_match"] is False
    assert parsed["sourcify_created_at"] == "2026-01-01T00:00:00"


def test_is_file_pending_etag():
    manifest = build_manifest_index(
        [
            {
                "table_name": TABLE_DEPLOYMENTS,
                "file_key": "v2/contract_deployments/a.parquet",
                "etag": '"abc"',
            }
        ]
    )
    assert is_file_pending(
        "abc",
        manifest,
        table_name=TABLE_DEPLOYMENTS,
        file_key="v2/contract_deployments/a.parquet",
        force=False,
    ) is False
    assert is_file_pending(
        "def",
        manifest,
        table_name=TABLE_DEPLOYMENTS,
        file_key="v2/contract_deployments/a.parquet",
        force=False,
    ) is True
    assert is_file_pending(
        "def",
        manifest,
        table_name=TABLE_DEPLOYMENTS,
        file_key="v2/contract_deployments/a.parquet",
        force=True,
    ) is True


def test_parse_batch_from_parquet_fixture(tmp_path: Path):
    dep_dir = tmp_path / TABLE_DEPLOYMENTS
    dep_dir.mkdir(parents=True)
    table = pa.table(
        {
            "id": ["dep-1"],
            "chain_id": pa.array([1], type=pa.int64()),
            "address": [bytes.fromhex("11" * 20)],
            "contract_id": ["ctr-1"],
        }
    )
    pq.write_table(table, dep_dir / "sample.parquet")

    rows = pq.read_table(dep_dir / "sample.parquet").to_pylist()
    parsed = parse_batch(TABLE_DEPLOYMENTS, rows)
    assert len(parsed) == 1
    assert parsed[0]["address"] == "0x" + "11" * 20

    ver_dir = tmp_path / TABLE_VERIFIED
    ver_dir.mkdir()
    vtable = pa.table(
        {
            "deployment_id": ["dep-1"],
            "compilation_id": ["cmp-1"],
            "creation_match": [True],
            "runtime_match": [True],
            "creation_metadata_match": [False],
            "runtime_metadata_match": [False],
            "created_at": ["2026-01-01T00:00:00"],
            "updated_at": ["2026-01-02T00:00:00"],
        }
    )
    pq.write_table(vtable, ver_dir / "sample.parquet")
    vrows = pq.read_table(ver_dir / "sample.parquet").to_pylist()
    vparsed = parse_batch(TABLE_VERIFIED, vrows)
    assert len(vparsed) == 1
    assert vparsed[0]["deployment_id"] == "dep-1"
