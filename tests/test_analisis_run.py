"""Unit tests for analisis_run orchestration (mocked HTTP)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from workers.analisis_run.edge_client import EdgeCallResult, is_retryable, parse_retry_after_ms
from workers.analisis_run import pipelines


def test_is_retryable_504() -> None:
    assert is_retryable(504, {"error": "Gateway Timeout"})
    assert is_retryable(429, {})
    assert not is_retryable(400, {"error": "invalid"})


def test_parse_retry_after_ms_body() -> None:
    assert parse_retry_after_ms(None, "", {"retryAfterMs": 1500}) == 1500.0
    assert parse_retry_after_ms(None, "Retry after 2000ms", {}) == 2000.0


def _ok(body: dict[str, Any], status: int = 200) -> EdgeCallResult:
    return EdgeCallResult(ok=True, status=status, body=body)


def _fail(error: str, status: int = 504) -> EdgeCallResult:
    return EdgeCallResult(ok=False, status=status, body={"error": error})


def test_estandar_empty_wallet_path() -> None:
    calls: list[str] = []

    def fake_call(name: str, body: dict[str, Any], **kwargs: Any) -> EdgeCallResult:
        calls.append(name)
        if name == "multichain-basica":
            return _ok({"chains": [], "upstream": {}, "coverage": {}})
        if name == "compliance-screen":
            return _ok({"status": "ok", "sdn_snapshot_at": None})
        if name == "analisis-empty-wallet":
            return _ok({
                "analisis": {"version": "analisis-v1", "tier": "estandar"},
                "evidencia": {"version": "evidencia-v1"},
                "upstream_errors": [],
                "compliance_column": {"status": "ok"},
                "compliance_ok": True,
            })
        raise AssertionError(f"unexpected edge {name}")

    with patch.object(pipelines, "call_edge", side_effect=fake_call):
        with patch.object(pipelines, "sleep_ms", return_value=None):
            out = pipelines.run_estandar_pipeline("0x" + "ab" * 20, "11111111-1111-4111-8111-111111111111")

    assert out["compliance_ok"] is True
    assert out["analisis"]["tier"] == "estandar"
    assert calls == ["multichain-basica", "compliance-screen", "analisis-empty-wallet"]


def test_estandar_full_graph_order() -> None:
    calls: list[str] = []
    chain = {"chain_id": 1, "ankr_slug": "eth", "name": "Ethereum", "ecosystem": "evm"}

    def fake_call(name: str, body: dict[str, Any], **kwargs: Any) -> EdgeCallResult:
        calls.append(name)
        if name == "multichain-basica":
            return _ok({"chains": [chain], "upstream": {}, "coverage": {}})
        if name == "compliance-screen":
            return _ok({"status": "ok"})
        if name == "analisis-portfolio":
            return _ok({"module": {"signals": {}, "grade": "B"}, "upstream": {}})
        if name == "analisis-multichain":
            return _ok({
                "module": {"signals": {}, "grade": "B"},
                "ranked_chains": [chain],
                "rank_method": "last_seen_proxy",
            })
        if name == "analisis-origins":
            # subject then hop
            if body.get("address", "").startswith("0xab"):
                return _ok({
                    "module": {"signals": {}, "grade": "B", "top_funders": []},
                    "top_funders": [],
                    "interaction_labels": [],
                    "tx_evidence": {},
                })
            return _ok({"module": {"signals": {}, "grade": "C"}, "interaction_labels": []})
        if name == "analisis-activity":
            return _ok({
                "module": {"signals": {}, "grade": "B"},
                "interaction_labels": [],
                "tx_evidence": {},
            })
        if name == "analisis-synthesize":
            return _ok({
                "analisis": {"version": "analisis-v1", "modules": {}},
                "evidencia": {"version": "evidencia-v1"},
                "upstream_errors": [],
                "compliance_column": {"status": "ok"},
                "compliance_ok": True,
            })
        if name == "analisis-custody":
            return _ok({"custody_classification": {"class": "unknown", "version": "custody_classification_v1"}})
        raise AssertionError(f"unexpected {name} {body}")

    with patch.object(pipelines, "call_edge", side_effect=fake_call):
        with patch.object(pipelines, "sleep_ms", return_value=None):
            out = pipelines.run_estandar_pipeline("0x" + "ab" * 20, "11111111-1111-4111-8111-111111111111")

    assert out["analisis"]["custody_classification"]["class"] == "unknown"
    assert calls[0] == "multichain-basica"
    assert "analisis-synthesize" in calls
    assert calls[-1] == "analisis-custody"
    assert "analisis-portfolio" in calls
    assert "analisis-origins" in calls


def test_estandar_fails_on_origins_504() -> None:
    chain = {"chain_id": 1, "ankr_slug": "eth", "name": "Ethereum", "ecosystem": "evm"}

    def fake_call(name: str, body: dict[str, Any], **kwargs: Any) -> EdgeCallResult:
        if name == "multichain-basica":
            return _ok({"chains": [chain], "upstream": {}})
        if name == "compliance-screen":
            return _ok({"status": "ok"})
        if name == "analisis-portfolio":
            return _ok({"module": {"signals": {}}, "upstream": {}})
        if name == "analisis-multichain":
            return _ok({"module": {"signals": {}}, "ranked_chains": [chain]})
        if name == "analisis-origins":
            return _fail("gateway_timeout", 504)
        if name == "analisis-activity":
            return _ok({"module": {"signals": {}}})
        raise AssertionError(name)

    with patch.object(pipelines, "call_edge", side_effect=fake_call):
        with patch.object(pipelines, "sleep_ms", return_value=None):
            with pytest.raises(RuntimeError, match="origins_"):
                pipelines.run_estandar_pipeline("0x" + "cd" * 20, "22222222-2222-4222-8222-222222222222")


def test_process_row_marks_failed() -> None:
    from workers.analisis_run import job

    sb = MagicMock()
    sb.rpc.return_value.execute.return_value.data = {"id": "rid", "status": "running"}

    with patch.object(job, "run_pipeline", side_effect=RuntimeError("boom")):
        with patch.object(job, "update_request", return_value={}) as upd:
            result = job.process_row(
                sb,
                {"id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "tier": "estandar", "wallet": "0x" + "11" * 20},
            )

    assert result["status"] == "failed"
    # last update should be failed
    failed_calls = [c for c in upd.call_args_list if c.args[2].get("status") == "failed"]
    assert failed_calls
