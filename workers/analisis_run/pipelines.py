"""Estándar / Experta orchestration graphs — HTTP only (no scoring in Python)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from workers.analisis_run.edge_client import EdgeCallResult, call_edge, sleep_ms
from workers.analisis_run.stages import (
    STAGE_ACTIVITY,
    STAGE_COMPLIANCE,
    STAGE_CUSTODY,
    STAGE_EMPTY_WALLET,
    STAGE_HOPS,
    STAGE_LIGHTS,
    STAGE_MULTICHAIN_MODULE,
    STAGE_OLA1,
    STAGE_ORIGINS,
    STAGE_PORTFOLIO,
    STAGE_SYNTHESIZE,
    stage,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _err(result: EdgeCallResult, prefix: str) -> str:
    body = result.body or {}
    return f"{prefix}_{body.get('error') or result.status}"


def _normalize_chains(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(item)
    return out


def _module(result: EdgeCallResult) -> dict[str, Any]:
    mod = result.body.get("module")
    return mod if isinstance(mod, dict) else {}


def run_estandar_pipeline(wallet: str, request_id: str, sb: Any = None) -> dict[str, Any]:
    generated_at = _now_iso()
    wallet = wallet.lower()

    with stage(sb, request_id, STAGE_OLA1):
        mc_loader = call_edge(
            "multichain-basica",
            {"address": wallet, "tier": "estandar", "include_upstream": True},
            timeout_ms=120_000,
            label="multichain-basica",
        )
    sleep_ms(500)
    with stage(sb, request_id, STAGE_COMPLIANCE):
        compliance = call_edge(
            "compliance-screen",
            {"address": wallet, "preview": False, "verify_signature": True},
            timeout_ms=120_000,
            label="compliance-screen",
        )
    if not mc_loader.ok:
        raise RuntimeError(_err(mc_loader, "multichain"))

    mc_body = mc_loader.body
    chains = _normalize_chains(mc_body.get("chains"))
    compliance_response = compliance.body if compliance.ok else {
        "error": compliance.body.get("error") or "compliance_failed",
        "detail": compliance.body,
    }

    if len(chains) == 0:
        with stage(sb, request_id, STAGE_EMPTY_WALLET):
            empty = call_edge(
                "analisis-empty-wallet",
                {
                    "address": wallet,
                    "tier": "estandar",
                    "request_id": request_id,
                    "generated_at": generated_at,
                    "compliance_response": compliance_response,
                    "mc_body": mc_body,
                },
                timeout_ms=120_000,
                label="analisis-empty-wallet",
            )
            if not empty.ok:
                raise RuntimeError(_err(empty, "empty_wallet"))
        return {
            "analisis": empty.body["analisis"],
            "evidencia": empty.body["evidencia"],
            "upstream_errors": empty.body.get("upstream_errors") or [],
            "compliance_column": empty.body.get("compliance_column"),
            "compliance_ok": bool(empty.body.get("compliance_ok")),
            "generated_at": generated_at,
        }

    with stage(sb, request_id, STAGE_PORTFOLIO):
        portfolio = call_edge(
            "analisis-portfolio",
            {"address": wallet, "tier": "estandar"},
            timeout_ms=120_000,
            label="analisis-portfolio",
        )
    sleep_ms(500)
    with stage(sb, request_id, STAGE_MULTICHAIN_MODULE):
        mc_mod = call_edge(
            "analisis-multichain",
            {"chains": chains, "tier": "estandar"},
            timeout_ms=30_000,
            label="analisis-multichain",
        )
    if not mc_mod.ok:
        raise RuntimeError(_err(mc_mod, "multichain_module"))
    if not portfolio.ok:
        raise RuntimeError(_err(portfolio, "portfolio"))

    ranked = mc_mod.body.get("ranked_chains") or []
    rank_method = str(mc_mod.body.get("rank_method") or "last_seen_proxy")
    multichain = _module(mc_mod)
    portfolio_mod = _module(portfolio)

    with stage(sb, request_id, STAGE_ORIGINS):
        origins = call_edge(
            "analisis-origins",
            {"address": wallet, "chains": ranked, "tier": "estandar"},
            timeout_ms=240_000,
            label="analisis-origins",
        )
    with stage(sb, request_id, STAGE_ACTIVITY):
        activity = call_edge(
            "analisis-activity",
            {"address": wallet, "chains": ranked, "tier": "estandar"},
            timeout_ms=240_000,
            label="analisis-activity",
        )
    sleep_ms(500)
    if not origins.ok:
        raise RuntimeError(_err(origins, "origins"))
    if not activity.ok:
        raise RuntimeError(_err(activity, "activity"))

    origins_mod = _module(origins)
    activity_mod = _module(activity)
    top_funders = origins.body.get("top_funders") or origins_mod.get("top_funders") or []
    if not isinstance(top_funders, list):
        top_funders = []

    hop_results: list[dict[str, Any]] = []
    hop_tx: list[Any] = []
    hop_labels: list[Any] = []
    with stage(sb, request_id, STAGE_HOPS):
        for funder in top_funders[:2]:
            if not isinstance(funder, dict):
                continue
            addr = str(funder.get("address") or "").lower()
            weight = funder.get("weight")
            hop = call_edge(
                "analisis-origins",
                {"address": addr, "chains": ranked, "tier": "estandar"},
                timeout_ms=180_000,
                label=f"origins-hop1:{addr[:10]}",
            )
            if hop.ok:
                hop_results.append({
                    "address": addr,
                    "weight": weight,
                    "hop": 1,
                    "module": hop.body.get("module"),
                })
                if hop.body.get("tx_evidence") is not None:
                    hop_tx.append(hop.body["tx_evidence"])
                if isinstance(hop.body.get("interaction_labels"), list):
                    hop_labels.extend(hop.body["interaction_labels"])
            else:
                hop_results.append({
                    "address": addr,
                    "weight": weight,
                    "hop": 1,
                    "error": hop.body.get("error") or f"http_{hop.status}",
                })

    label_sources: list[Any] = []
    for src in (
        origins.body.get("interaction_labels"),
        activity.body.get("interaction_labels"),
        hop_labels,
    ):
        if isinstance(src, list):
            label_sources.extend(src)

    with stage(sb, request_id, STAGE_SYNTHESIZE):
        synth = call_edge(
            "analisis-synthesize",
            {
                "address": wallet,
                "tier": "estandar",
                "request_id": request_id,
                "generated_at": generated_at,
                "modules": {
                    "multichain": multichain,
                    "origins": origins_mod,
                    "activity": activity_mod,
                    "portfolio": portfolio_mod,
                },
                "hop_results": hop_results,
                "interaction_label_sources": label_sources,
                "compliance_response": compliance_response,
                "run_params": {
                    "rank_method": rank_method,
                    "origins_tx_cap": 250,
                    "activity_window_days": 45,
                    "hops": 1,
                    "hop_funders": top_funders[:2],
                    "chains_ranked": ranked,
                    "multichain_coverage": mc_body.get("coverage"),
                    "ofac_layers": {
                        "A": "compliance-screen wallet objetivo",
                        "B": "ofac_sdn_addresses via lookup_interaction_quality",
                    },
                },
                "tx_evidence": {
                    "origins": origins.body.get("tx_evidence"),
                    "activity": activity.body.get("tx_evidence"),
                    "origins_hops": hop_tx,
                },
                "upstream": {
                    "multichain": mc_body.get("upstream") or {"provider": "goldrush", "calls": []},
                    "portfolio": portfolio.body.get("upstream") or {"provider": "zerion"},
                },
                "mc_upstream_errors": mc_body.get("upstream_errors")
                if isinstance(mc_body.get("upstream_errors"), list)
                else [],
                "portfolio_upstream_error": (
                    (portfolio.body.get("upstream") or {}).get("error")
                    if isinstance(portfolio.body.get("upstream"), dict)
                    else None
                ),
            },
            timeout_ms=120_000,
            label="analisis-synthesize",
        )
        if not synth.ok:
            raise RuntimeError(_err(synth, "synthesize"))

    analisis = dict(synth.body.get("analisis") or {})
    evidencia = dict(synth.body.get("evidencia") or {})
    custody_chains = _normalize_chains(ranked) or chains
    with stage(sb, request_id, STAGE_CUSTODY):
        custody = call_edge(
            "analisis-custody",
            {
                "address": wallet,
                "tier": "estandar",
                "chains": custody_chains,
                "activity_signals": (activity_mod.get("signals") or activity_mod),
                "multichain_signals": (multichain.get("signals") or multichain),
                "portfolio_signals": (portfolio_mod.get("signals") or portfolio_mod),
                "origins_signals": (origins_mod.get("signals") or origins_mod),
            },
            timeout_ms=180_000,
            label="analisis-custody",
        )
        if not custody.ok:
            raise RuntimeError(_err(custody, "custody"))
    analisis["custody_classification"] = custody.body.get("custody_classification")

    return {
        "analisis": analisis,
        "evidencia": evidencia,
        "upstream_errors": synth.body.get("upstream_errors") or [],
        "compliance_column": synth.body.get("compliance_column"),
        "compliance_ok": bool(synth.body.get("compliance_ok")),
        "generated_at": generated_at,
    }


def _run_origins_hop(
    address: str,
    chains: list[Any],
    hop: int,
    weight: Any,
) -> dict[str, Any]:
    hop_res = call_edge(
        "analisis-origins",
        {"address": address, "chains": chains, "tier": "experta"},
        timeout_ms=180_000,
        label=f"origins-hop{hop}:{address[:10]}",
    )
    if hop_res.ok:
        mod = hop_res.body.get("module") or {}
        top = hop_res.body.get("top_funders") or (mod.get("top_funders") if isinstance(mod, dict) else []) or []
        return {
            "entry": {
                "address": address,
                "weight": weight,
                "hop": hop,
                "module": mod,
            },
            "tx_evidence": hop_res.body.get("tx_evidence"),
            "labels": hop_res.body.get("interaction_labels")
            if isinstance(hop_res.body.get("interaction_labels"), list)
            else [],
            "top_funders": top if isinstance(top, list) else [],
        }
    return {
        "entry": {
            "address": address,
            "weight": weight,
            "hop": hop,
            "error": hop_res.body.get("error") or f"http_{hop_res.status}",
        },
        "tx_evidence": None,
        "labels": [],
        "top_funders": [],
    }


def _run_basica_light(cp: dict[str, Any]) -> dict[str, Any]:
    addr = str(cp.get("address") or "").lower()
    weight = cp.get("weight")
    try:
        mc_loader = call_edge(
            "multichain-basica",
            {"address": addr, "tier": "basica", "include_upstream": True},
            timeout_ms=60_000,
            label=f"light-mc:{addr[:10]}",
        )
        if not mc_loader.ok:
            return {
                "address": addr,
                "weight": weight,
                "tier": "basica",
                "compliance_screen": False,
                "error": _err(mc_loader, "multichain"),
            }
        chains = _normalize_chains(mc_loader.body.get("chains"))
        mc_mod = call_edge(
            "analisis-multichain",
            {"chains": chains, "tier": "basica"},
            timeout_ms=30_000,
            label=f"light-mcm:{addr[:10]}",
        )
        if not mc_mod.ok:
            return {
                "address": addr,
                "weight": weight,
                "tier": "basica",
                "compliance_screen": False,
                "error": _err(mc_mod, "multichain_module"),
            }
        ranked = mc_mod.body.get("ranked_chains") or []
        multichain = _module(mc_mod)
        origins = call_edge(
            "analisis-origins",
            {"address": addr, "chains": ranked, "tier": "basica"},
            timeout_ms=120_000,
            label=f"light-origins:{addr[:10]}",
        )
        activity = call_edge(
            "analisis-activity",
            {"address": addr, "chains": ranked, "tier": "basica"},
            timeout_ms=120_000,
            label=f"light-activity:{addr[:10]}",
        )
        if not origins.ok:
            return {
                "address": addr,
                "weight": weight,
                "tier": "basica",
                "compliance_screen": False,
                "error": _err(origins, "origins"),
            }
        if not activity.ok:
            return {
                "address": addr,
                "weight": weight,
                "tier": "basica",
                "compliance_screen": False,
                "error": _err(activity, "activity"),
            }
        label_sources: list[Any] = []
        for src in (origins.body.get("interaction_labels"), activity.body.get("interaction_labels")):
            if isinstance(src, list):
                label_sources.extend(src)
        synth = call_edge(
            "analisis-synthesize",
            {
                "address": addr,
                "tier": "basica",
                "modules": {
                    "multichain": multichain,
                    "origins": _module(origins),
                    "activity": _module(activity),
                    "portfolio": None,
                },
                "interaction_label_sources": label_sources,
            },
            timeout_ms=60_000,
            label=f"light-synth:{addr[:10]}",
        )
        if not synth.ok:
            return {
                "address": addr,
                "weight": weight,
                "tier": "basica",
                "compliance_screen": False,
                "error": _err(synth, "synthesize"),
            }
        return {
            "address": addr,
            "weight": weight,
            "tier": "basica",
            "compliance_screen": False,
            "analisis": synth.body.get("analisis"),
            "tx_evidence": {
                "origins": origins.body.get("tx_evidence"),
                "activity": activity.body.get("tx_evidence"),
            },
            "interaction_labels": synth.body.get("interaction_labels") or [],
            "multichain_upstream": mc_loader.body.get("upstream"),
        }
    except Exception as e:  # noqa: BLE001
        return {
            "address": addr,
            "weight": weight,
            "tier": "basica",
            "compliance_screen": False,
            "error": str(e)[:300],
        }


def run_experta_pipeline(wallet: str, request_id: str, sb: Any = None) -> dict[str, Any]:
    generated_at = _now_iso()
    wallet = wallet.lower()

    with stage(sb, request_id, STAGE_OLA1):
        mc_loader = call_edge(
            "multichain-basica",
            {"address": wallet, "tier": "experta", "include_upstream": True},
            timeout_ms=120_000,
            label="multichain-basica",
        )
    sleep_ms(500)
    with stage(sb, request_id, STAGE_COMPLIANCE):
        compliance = call_edge(
            "compliance-screen",
            {"address": wallet, "preview": False, "verify_signature": True},
            timeout_ms=120_000,
            label="compliance-screen",
        )
    if not mc_loader.ok:
        raise RuntimeError(_err(mc_loader, "multichain"))

    mc_body = mc_loader.body
    chains = _normalize_chains(mc_body.get("chains"))
    compliance_response = compliance.body if compliance.ok else {
        "error": compliance.body.get("error") or "compliance_failed",
        "detail": compliance.body,
    }

    if len(chains) == 0:
        with stage(sb, request_id, STAGE_EMPTY_WALLET):
            empty = call_edge(
                "analisis-empty-wallet",
                {
                    "address": wallet,
                    "tier": "experta",
                    "request_id": request_id,
                    "generated_at": generated_at,
                    "compliance_response": compliance_response,
                    "mc_body": mc_body,
                },
                timeout_ms=120_000,
                label="analisis-empty-wallet",
            )
            if not empty.ok:
                raise RuntimeError(_err(empty, "empty_wallet"))
        return {
            "analisis": empty.body["analisis"],
            "evidencia": empty.body["evidencia"],
            "upstream_errors": empty.body.get("upstream_errors") or [],
            "compliance_column": empty.body.get("compliance_column"),
            "compliance_ok": bool(empty.body.get("compliance_ok")),
            "generated_at": generated_at,
        }

    with stage(sb, request_id, STAGE_PORTFOLIO):
        portfolio = call_edge(
            "analisis-portfolio",
            {"address": wallet, "tier": "experta"},
            timeout_ms=120_000,
            label="analisis-portfolio",
        )
    sleep_ms(500)
    with stage(sb, request_id, STAGE_MULTICHAIN_MODULE):
        mc_mod = call_edge(
            "analisis-multichain",
            {"chains": chains, "tier": "experta"},
            timeout_ms=30_000,
            label="analisis-multichain",
        )
    if not mc_mod.ok:
        raise RuntimeError(_err(mc_mod, "multichain_module"))
    if not portfolio.ok:
        raise RuntimeError(_err(portfolio, "portfolio"))

    ranked = mc_mod.body.get("ranked_chains") or []
    rank_method = str(mc_mod.body.get("rank_method") or "last_seen_proxy")
    multichain = _module(mc_mod)
    portfolio_mod = _module(portfolio)

    with stage(sb, request_id, STAGE_ORIGINS):
        origins = call_edge(
            "analisis-origins",
            {"address": wallet, "chains": ranked, "tier": "experta"},
            timeout_ms=240_000,
            label="analisis-origins",
        )
    with stage(sb, request_id, STAGE_ACTIVITY):
        activity = call_edge(
            "analisis-activity",
            {"address": wallet, "chains": ranked, "tier": "experta"},
            timeout_ms=240_000,
            label="analisis-activity",
        )
    sleep_ms(500)
    if not origins.ok:
        raise RuntimeError(_err(origins, "origins"))
    if not activity.ok:
        raise RuntimeError(_err(activity, "activity"))

    origins_mod = _module(origins)
    activity_mod = _module(activity)
    top_funders = origins.body.get("top_funders") or origins_mod.get("top_funders") or []
    if not isinstance(top_funders, list):
        top_funders = []
    top_cps = activity.body.get("top_counterparties") or activity_mod.get("top_counterparties") or []
    if not isinstance(top_cps, list):
        top_cps = []

    hop_results: list[dict[str, Any]] = []
    hop_tx: list[Any] = []
    hop_labels: list[Any] = []
    hop1_ok: list[dict[str, Any]] = []

    with stage(sb, request_id, STAGE_HOPS):
        for funder in top_funders[:2]:
            if not isinstance(funder, dict):
                continue
            addr = str(funder.get("address") or "").lower()
            hop1 = _run_origins_hop(addr, ranked if isinstance(ranked, list) else [], 1, funder.get("weight"))
            hop_results.append(hop1["entry"])
            if hop1["tx_evidence"] is not None:
                hop_tx.append(hop1["tx_evidence"])
            hop_labels.extend(hop1["labels"])
            if not hop1["entry"].get("error"):
                hop1_ok.append({
                    "address": addr,
                    "weight": funder.get("weight"),
                    "top_funders": hop1["top_funders"],
                })
            sleep_ms(750)

        for h1 in hop1_ok:
            for funder2 in (h1.get("top_funders") or [])[:2]:
                if not isinstance(funder2, dict):
                    continue
                addr2 = str(funder2.get("address") or "").lower()
                if addr2 == wallet:
                    continue
                hop2 = _run_origins_hop(addr2, ranked if isinstance(ranked, list) else [], 2, funder2.get("weight"))
                entry = dict(hop2["entry"])
                entry["via"] = h1["address"]
                hop_results.append(entry)
                if hop2["tx_evidence"] is not None:
                    hop_tx.append(hop2["tx_evidence"])
                hop_labels.extend(hop2["labels"])
                sleep_ms(750)

    light_targets = [cp for cp in top_cps[:5] if isinstance(cp, dict)]
    light_results: list[dict[str, Any]] = []
    with stage(sb, request_id, STAGE_LIGHTS):
        for i, cp in enumerate(light_targets):
            if i > 0:
                sleep_ms(1000)
            light_results.append(_run_basica_light(cp))

    light_labels: list[Any] = []
    light_tx: list[Any] = []
    for light in light_results:
        if isinstance(light.get("interaction_labels"), list):
            light_labels.extend(light["interaction_labels"])
        if light.get("tx_evidence") is not None:
            light_tx.append(light["tx_evidence"])

    label_sources: list[Any] = []
    for src in (
        origins.body.get("interaction_labels"),
        activity.body.get("interaction_labels"),
        hop_labels,
        light_labels,
    ):
        if isinstance(src, list):
            label_sources.extend(src)

    with stage(sb, request_id, STAGE_SYNTHESIZE):
        synth = call_edge(
            "analisis-synthesize",
            {
                "address": wallet,
                "tier": "experta",
                "request_id": request_id,
                "generated_at": generated_at,
                "modules": {
                    "multichain": multichain,
                    "origins": origins_mod,
                    "activity": activity_mod,
                    "portfolio": portfolio_mod,
                },
                "hop_results": hop_results,
                "light_results": light_results,
                "interaction_label_sources": label_sources,
                "compliance_response": compliance_response,
                "run_params": {
                    "rank_method": rank_method,
                    "origins_tx_cap": 500,
                    "activity_window_days": 90,
                    "hops": 2,
                    "hop_funders": top_funders[:2],
                    "activity_light": {
                        "n": 5,
                        "mode": "basica_embedded",
                        "compliance_screen": False,
                        "counterparties": light_targets,
                    },
                    "chains_ranked": ranked,
                    "multichain_coverage": mc_body.get("coverage"),
                    "ofac_layers": {
                        "A": "compliance-screen wallet objetivo only",
                        "B": "ofac_sdn_addresses via IQ (target + hops + lights modules)",
                        "lights": "no compliance-screen",
                    },
                },
                "tx_evidence": {
                    "origins": origins.body.get("tx_evidence"),
                    "activity": activity.body.get("tx_evidence"),
                    "origins_hops": hop_tx,
                    "activity_lights": light_tx,
                },
                "upstream": {
                    "multichain": mc_body.get("upstream") or {"provider": "goldrush", "calls": []},
                    "portfolio": portfolio.body.get("upstream") or {"provider": "zerion"},
                },
                "mc_upstream_errors": mc_body.get("upstream_errors")
                if isinstance(mc_body.get("upstream_errors"), list)
                else [],
                "portfolio_upstream_error": (
                    (portfolio.body.get("upstream") or {}).get("error")
                    if isinstance(portfolio.body.get("upstream"), dict)
                    else None
                ),
            },
            timeout_ms=120_000,
            label="analisis-synthesize",
        )
        if not synth.ok:
            raise RuntimeError(_err(synth, "synthesize"))

    analisis = dict(synth.body.get("analisis") or {})
    evidencia = dict(synth.body.get("evidencia") or {})
    custody_chains = _normalize_chains(ranked) or chains
    with stage(sb, request_id, STAGE_CUSTODY):
        custody = call_edge(
            "analisis-custody",
            {
                "address": wallet,
                "tier": "experta",
                "chains": custody_chains,
                "activity_signals": (activity_mod.get("signals") or activity_mod),
                "multichain_signals": (multichain.get("signals") or multichain),
                "portfolio_signals": (portfolio_mod.get("signals") or portfolio_mod),
                "origins_signals": (origins_mod.get("signals") or origins_mod),
            },
            timeout_ms=240_000,
            label="analisis-custody",
        )
        if not custody.ok:
            raise RuntimeError(_err(custody, "custody"))
    analisis["custody_classification"] = custody.body.get("custody_classification")

    return {
        "analisis": analisis,
        "evidencia": evidencia,
        "upstream_errors": synth.body.get("upstream_errors") or [],
        "compliance_column": synth.body.get("compliance_column"),
        "compliance_ok": bool(synth.body.get("compliance_ok")),
        "generated_at": generated_at,
    }


def run_pipeline(tier: str, wallet: str, request_id: str, sb: Any = None) -> dict[str, Any]:
    if tier == "estandar":
        return run_estandar_pipeline(wallet, request_id, sb=sb)
    if tier == "experta":
        return run_experta_pipeline(wallet, request_id, sb=sb)
    raise ValueError(f"unsupported_tier:{tier}")


def call_entregables(request_id: str, final_status: str) -> EdgeCallResult:
    return call_edge(
        "analisis-entregables",
        {"request_id": request_id, "final_status": final_status},
        timeout_ms=120_000,
        max_attempts=3,
        label="analisis-entregables",
    )
