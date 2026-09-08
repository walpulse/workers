"""Unit tests for analisis_run orchestration (mocked HTTP)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from workers.analisis_run.edge_client import EdgeCallResult, is_retryable, parse_retry_after_ms
from workers.analisis_run import pipelines
from workers.analisis_run import stages as stage_mod


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
    stage_names: list[str] = []
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

    sb = MagicMock()

    def track_start(_sb: Any, _rid: str, name: str, meta: Any = None) -> dict[str, Any]:
        stage_names.append(name)
        return {}

    with patch.object(pipelines, "call_edge", side_effect=fake_call):
        with patch.object(pipelines, "sleep_ms", return_value=None):
            with patch.object(stage_mod, "start_stage", side_effect=track_start):
                with patch.object(stage_mod, "finish_stage", return_value={}):
                    out = pipelines.run_estandar_pipeline(
                        "0x" + "ab" * 20,
                        "11111111-1111-4111-8111-111111111111",
                        sb=sb,
                    )

    assert out["analisis"]["custody_classification"]["class"] == "unknown"
    assert calls[0] == "multichain-basica"
    assert "analisis-synthesize" in calls
    assert calls[-1] == "analisis-custody"
    assert "analisis-portfolio" in calls
    assert "analisis-origins" in calls
    assert stage_names[0] == stage_mod.STAGE_OLA1
    assert stage_mod.STAGE_SYNTHESIZE in stage_names
    assert stage_names[-1] == stage_mod.STAGE_CUSTODY


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
    failed_calls = [c for c in upd.call_args_list if c.args[2].get("status") == "failed"]
    assert failed_calls


def test_process_rows_parallel_uses_pool() -> None:
    from workers.analisis_run import job

    rows = [
        {"id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "tier": "estandar", "wallet": "0x" + "11" * 20},
        {"id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "tier": "estandar", "wallet": "0x" + "22" * 20},
    ]
    seen_ids: list[str] = []

    def fake_process(_sb: Any, row: dict[str, Any]) -> dict[str, Any]:
        seen_ids.append(str(row["id"]))
        return {"id": row["id"], "status": "succeeded"}

    with patch.object(job, "supabase_client", return_value=MagicMock()):
        with patch.object(job, "process_row", side_effect=fake_process):
            results = job.process_rows_parallel(rows, max_workers=2)

    assert len(results) == 2
    assert {r["id"] for r in results} == {rows[0]["id"], rows[1]["id"]}
    assert set(seen_ids) == {rows[0]["id"], rows[1]["id"]}


def test_stage_context_records_failed() -> None:
    sb = MagicMock()
    starts: list[str] = []
    finishes: list[tuple[str, str]] = []

    def fake_start(_sb: Any, _rid: str, name: str, meta: Any = None) -> dict[str, Any]:
        starts.append(name)
        return {}

    def fake_finish(
        _sb: Any,
        _rid: str,
        name: str,
        *,
        status: str = "succeeded",
        error: str | None = None,
        meta: Any = None,
    ) -> dict[str, Any]:
        finishes.append((name, status))
        return {}

    with patch.object(stage_mod, "start_stage", side_effect=fake_start):
        with patch.object(stage_mod, "finish_stage", side_effect=fake_finish):
            with pytest.raises(RuntimeError, match="boom"):
                with stage_mod.stage(sb, "rid", stage_mod.STAGE_OLA1):
                    raise RuntimeError("boom")

    assert starts == [stage_mod.STAGE_OLA1]
    assert finishes == [(stage_mod.STAGE_OLA1, "failed")]


def test_cex_skip_info_from_label() -> None:
    info = pipelines._cex_skip_info(
        "0x" + "aa" * 20,
        label_map={"0x" + "aa" * 20: {"categories": ["cex"], "cex_name": "Binance"}},
        sb=None,
    )
    assert info is not None
    assert info["skip_reason"] == "cex_label"
    assert info["cex_name"] == "Binance"


def test_cex_skip_info_from_catalog() -> None:
    sb = MagicMock()
    sb.rpc.return_value.execute.return_value.data = [
        {"address": "0x" + "bb" * 20, "cex_name": "Coinbase", "distinct_name": "coinbase"}
    ]
    info = pipelines._cex_skip_info("0x" + "bb" * 20, label_map={}, sb=sb)
    assert info is not None
    assert info["skip_reason"] == "cex_catalog"


def test_experta_skips_cex_hop_and_light() -> None:
    calls: list[tuple[str, str]] = []
    chain = {"chain_id": 1, "ankr_slug": "eth", "name": "Ethereum", "ecosystem": "evm"}
    cex = "0x" + "ce" * 20
    peer = "0x" + "11" * 20
    subject = "0x" + "ab" * 20

    def fake_call(name: str, body: dict[str, Any], **kwargs: Any) -> EdgeCallResult:
        addr = str(body.get("address") or "").lower()
        calls.append((name, addr))
        if addr == cex and name in {"analisis-origins", "multichain-basica", "analisis-activity"}:
            raise AssertionError(f"must not expand CEX via {name}")
        if name == "multichain-basica":
            return _ok({"chains": [chain], "upstream": {}, "coverage": {}})
        if name == "compliance-screen":
            return _ok({"status": "ok"})
        if name == "analisis-portfolio":
            return _ok({"module": {"signals": {}}, "upstream": {}})
        if name == "analisis-multichain":
            return _ok({"module": {"signals": {}}, "ranked_chains": [chain], "rank_method": "x"})
        if name == "analisis-origins" and addr == subject:
            return _ok({
                "module": {"signals": {}, "top_funders": [{"address": cex, "weight": 1}]},
                "top_funders": [{"address": cex, "weight": 1}],
                "interaction_labels": [{"address": cex, "categories": ["cex"], "cex_name": "Kraken"}],
                "tx_evidence": {},
            })
        if name == "analisis-activity" and addr == subject:
            return _ok({
                "module": {
                    "signals": {},
                    "top_counterparties": [
                        {"address": cex, "weight": 1},
                        {"address": peer, "weight": 0.5},
                    ],
                },
                "top_counterparties": [
                    {"address": cex, "weight": 1},
                    {"address": peer, "weight": 0.5},
                ],
                "interaction_labels": [{"address": cex, "categories": ["cex"], "cex_name": "Kraken"}],
                "tx_evidence": {},
            })
        if name in {"analisis-origins", "analisis-activity"}:
            return _ok({"module": {"signals": {}}, "interaction_labels": [], "tx_evidence": {}})
        if name == "analisis-synthesize":
            if body.get("tier") == "basica":
                return _ok({
                    "analisis": {"tier": "basica", "modules": {}},
                    "evidencia": {},
                    "upstream_errors": [],
                    "compliance_ok": True,
                })
            return _ok({
                "analisis": {"version": "analisis-v1", "modules": {}},
                "evidencia": {"version": "evidencia-v1"},
                "upstream_errors": [],
                "compliance_column": {"status": "ok"},
                "compliance_ok": True,
            })
        if name == "analisis-custody":
            return _ok({"custody_classification": {"class": "unknown"}})
        raise AssertionError(f"unexpected {name} {body}")

    with patch.object(pipelines, "call_edge", side_effect=fake_call):
        with patch.object(pipelines, "sleep_ms", return_value=None):
            out = pipelines.run_experta_pipeline(subject, "33333333-3333-4333-8333-333333333333", sb=None)

    assert out["delivery_warnings"] is True
    assert any(e.get("error") == "cex_label" for e in out["upstream_errors"] if isinstance(e, dict))
    assert ("analisis-origins", cex) not in calls
    assert ("multichain-basica", cex) not in calls
    assert ("multichain-basica", peer) in calls


def test_limit_clamped_to_five() -> None:
    from workers.analisis_run import job

    with patch.object(job, "supabase_client", return_value=MagicMock()):
        with patch.object(job, "claim_pending", return_value=[]) as claim:
            code = job.main(["--limit", "99"])
    assert code == 0
    assert claim.call_args.kwargs["limit"] == 5
