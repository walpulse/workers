"""Unit tests for sourcify_verified job helpers (chunk / timeout retry)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from postgrest.exceptions import APIError

from workers.sourcify_verified import job


def test_chunked_respects_append_size():
    rows = [{"i": i} for i in range(1200)]
    batches = job.chunked(rows, job.APPEND_CHUNK)
    assert job.APPEND_CHUNK == 500
    assert len(batches) == 3
    assert len(batches[0]) == 500
    assert len(batches[-1]) == 200


def test_is_statement_timeout_detects_57014():
    exc = APIError({"message": "canceling statement due to statement timeout", "code": "57014"})
    assert job._is_statement_timeout(exc) is True
    assert job._is_statement_timeout(APIError({"message": "other", "code": "23505"})) is False
    assert job._is_statement_timeout(RuntimeError("nope")) is False


def test_upsert_batches_retries_statement_timeout(monkeypatch: pytest.MonkeyPatch):
    sleeps: list[float] = []
    monkeypatch.setattr(job.time, "sleep", lambda s: sleeps.append(s))

    calls = {"n": 0}

    class FakeRpc:
        def execute(self):
            calls["n"] += 1
            if calls["n"] < 3:
                raise APIError(
                    {"message": "canceling statement due to statement timeout", "code": "57014"}
                )
            return SimpleNamespace(data=2)

    class FakeSb:
        def rpc(self, _name: str, _payload: dict):
            return FakeRpc()

    total = job.upsert_batches(FakeSb(), "upsert_sourcify_deployments", [{"a": 1}, {"a": 2}])
    assert total == 2
    assert calls["n"] == 3
    assert sleeps == [1.0, 2.0]


def test_upsert_batches_raises_non_timeout():
    class FakeRpc:
        def execute(self):
            raise APIError({"message": "boom", "code": "PGRST301"})

    class FakeSb:
        def rpc(self, _name: str, _payload: dict):
            return FakeRpc()

    with pytest.raises(APIError):
        job.upsert_batches(FakeSb(), "upsert_sourcify_deployments", [{"a": 1}])


def test_run_error_path_does_not_mask_upsert_failure(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")

    sb = MagicMock()
    monkeypatch.setattr(job, "supabase_client", lambda: sb)
    monkeypatch.setattr(job, "load_manifest", lambda _sb: {})
    monkeypatch.setattr(
        job,
        "build_pending_queue",
        lambda *_a, **_k: [
            job.ExportFile(
                table_name=job.TABLE_DEPLOYMENTS,
                file_key="v2/contract_deployments/x.parquet",
                etag="e",
                size=10,
                last_modified=None,
            )
        ],
    )

    def boom(*_a, **_k):
        raise APIError({"message": "canceling statement due to statement timeout", "code": "57014"})

    monkeypatch.setattr(job, "ingest_parquet_file", boom)

    sync_calls: list[tuple[str, int]] = []

    def sync_fail(_sb, status: str, files_processed: int):
        sync_calls.append((status, files_processed))
        raise APIError({"message": "canceling statement due to statement timeout", "code": "57014"})

    monkeypatch.setattr(job, "update_sync_run", sync_fail)

    with pytest.raises(APIError) as ei:
        job.run(max_runtime_seconds=3600)
    assert getattr(ei.value, "code", None) == "57014" or "57014" in str(ei.value)
    assert sync_calls == [("error", 0)]
