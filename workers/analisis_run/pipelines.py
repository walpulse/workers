"""Estándar / Experta orchestration graphs — HTTP only (no scoring in Python)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from workers.analisis_run.edge_client import EdgeCallResult, call_edge, sleep_ms
from workers.analisis_run.module_fetch import (
    HOP_FUNDER_N,
    ZERO_EVM_ADDRESS,
    run_activity_partitioned,
    run_funder_risk,
    run_origins_partitioned,
)
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


def _soft_module_stub(*, stage: str, error: str, top_key: str) -> dict[str, Any]:
    """Minimal module payload when subject Origins/Activity Edge fails after retries."""
    return {
        "version": f"{stage}-soft-fail",
        "signals": {"error": error, "grade": None, "chains_ok": 0},
        "per_chain": [],
        "grade": None,
        top_key: [],
        "summary": {},
        "strengths": [],
        "concerns": [f"Module {stage} unavailable: {error}"],
        "highlights": [],
    }


def _labels_by_address(rows: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        addr = str(row.get("address") or "").lower()
        if not addr:
            continue
        prev = out.get(addr)
        if prev is None:
            out[addr] = dict(row)
            continue
        cats = list(prev.get("categories") or []) + list(row.get("categories") or [])
        prev["categories"] = sorted({str(c) for c in cats if c})
        if not prev.get("cex_name") and row.get("cex_name"):
            prev["cex_name"] = row.get("cex_name")
        out[addr] = prev
    return out


def _lookup_cex_catalog(sb: Any, address: str) -> dict[str, Any] | None:
    if sb is None or not address:
        return None
    try:
        data = sb.rpc("lookup_cex_address", {"p_address": address, "p_blockchain": "evm"}).execute().data
    except Exception:  # noqa: BLE001 — catalog miss must not kill pipeline
        return None
    if isinstance(data, list) and data:
        row = data[0]
        return row if isinstance(row, dict) else None
    if isinstance(data, dict) and data.get("address"):
        return data
    return None


_HOP2_BLOCK_CATS = frozenset({"ofac", "mixer", "cex", "cex_deposit_inferred", "bridge"})


def _cex_skip_info(
    address: str,
    *,
    label_map: dict[str, dict[str, Any]],
    sb: Any = None,
) -> dict[str, Any] | None:
    """If address is a known CEX, return skip metadata; else None."""
    addr = (address or "").lower()
    if not addr:
        return None
    label = label_map.get(addr) or {}
    cats = {str(c).lower() for c in (label.get("categories") or []) if c}
    if "cex" in cats or "cex_deposit_inferred" in cats:
        return {
            "skipped": True,
            "skip_reason": "cex_label",
            "cex_name": label.get("cex_name"),
        }
    catalog = _lookup_cex_catalog(sb, addr)
    if catalog:
        return {
            "skipped": True,
            "skip_reason": "cex_catalog",
            "cex_name": catalog.get("cex_name") or catalog.get("distinct_name"),
        }
    return None


def _hop2_target_skip(
    address: str,
    *,
    subject: str,
    label_map: dict[str, dict[str, Any]],
    sb: Any = None,
) -> dict[str, Any] | None:
    """Skip hop-2 when target is subject, zero, or risk entity (cex/bridge/mixer/ofac)."""
    addr = (address or "").lower()
    if not addr or addr == ZERO_EVM_ADDRESS:
        return {"skipped": True, "skip_reason": "zero_address"}
    if addr == subject.lower():
        return {"skipped": True, "skip_reason": "subject"}
    label = label_map.get(addr) or {}
    cats = {str(c).lower() for c in (label.get("categories") or []) if c}
    blocked = cats & _HOP2_BLOCK_CATS
    if blocked:
        reason = sorted(blocked)[0]
        return {
            "skipped": True,
            "skip_reason": f"{reason}_label",
            "cex_name": label.get("cex_name"),
        }
    return _cex_skip_info(addr, label_map=label_map, sb=sb)


def _merge_upstream_errors(base: Any, extra: list[Any]) -> list[Any]:
    out: list[Any] = []
    if isinstance(base, list):
        out.extend(base)
    out.extend(extra)
    return out


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
            {"address": wallet, "preview": False, "verify_signature": True, "mode": "multi"},
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
            "delivery_warnings": False,
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
        origins = run_origins_partitioned(wallet, _normalize_chains(ranked), "estandar")
        soft_errors_early: list[Any] = list(origins.body.get("soft_errors") or [])
        if not origins.ok:
            err = _err(origins, "origins")
            soft_errors_early.append({"stage": "origins", "error": err})
            origins = EdgeCallResult(
                ok=True,
                status=origins.status,
                body={
                    "module": _soft_module_stub(stage="origins", error=err, top_key="top_funders"),
                    "top_funders": [],
                    "interaction_labels": [],
                    "tx_evidence": [],
                    "chain_alerts": [],
                    "soft_failed": True,
                },
            )
    with stage(sb, request_id, STAGE_ACTIVITY):
        activity = run_activity_partitioned(wallet, _normalize_chains(ranked), "estandar")
        soft_errors_early.extend(list(activity.body.get("soft_errors") or []))
        if not activity.ok:
            err = _err(activity, "activity")
            soft_errors_early.append({"stage": "activity", "error": err})
            activity = EdgeCallResult(
                ok=True,
                status=activity.status,
                body={
                    "module": _soft_module_stub(
                        stage="activity", error=err, top_key="top_counterparties"
                    ),
                    "top_counterparties": [],
                    "interaction_labels": [],
                    "tx_evidence": [],
                    "chain_alerts": [],
                    "soft_failed": True,
                },
            )

    origins_mod = _module(origins)
    activity_mod = _module(activity)
    top_funders = origins.body.get("top_funders") or origins_mod.get("top_funders") or []
    if not isinstance(top_funders, list):
        top_funders = []
    hop_n = HOP_FUNDER_N["estandar"]

    label_map = _labels_by_address(origins.body.get("interaction_labels"))
    label_map.update(_labels_by_address(activity.body.get("interaction_labels")))

    soft_errors: list[Any] = list(soft_errors_early)
    with stage(sb, request_id, STAGE_HOPS):
        hop_results, hop_labels, hop_errs = _run_funder_risk_hops(
            wallet=wallet,
            tier="estandar",
            origins=origins,
            ranked=_normalize_chains(ranked),
            label_map=label_map,
            sb=sb,
            allow_hop2=False,
        )
        soft_errors.extend(hop_errs)
    hop_tx: list[Any] = []

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
                    "hop_mode": "funder_risk",
                    "hop_funders": top_funders[:hop_n],
                    "chains_ranked": ranked,
                    "multichain_coverage": mc_body.get("coverage"),
                    "ofac_layers": {
                        "A": "compliance-screen mode=multi (OFAC/UN/EU/HMT) wallet objetivo",
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
        "upstream_errors": _merge_upstream_errors(synth.body.get("upstream_errors"), soft_errors),
        "compliance_column": synth.body.get("compliance_column"),
        "compliance_ok": bool(synth.body.get("compliance_ok")),
        "delivery_warnings": bool(soft_errors),
        "generated_at": generated_at,
    }


def _chain_from_hint(hint: dict[str, Any], ranked: list[dict[str, Any]]) -> dict[str, Any] | None:
    cid = hint.get("chain_id")
    slug = str(hint.get("ankr_slug") or "")
    for c in ranked:
        if cid is not None and c.get("chain_id") == cid:
            return c
        if slug and c.get("ankr_slug") == slug:
            return c
    if ranked:
        return ranked[0]
    if cid is not None or slug:
        return {
            "chain_id": cid,
            "ankr_slug": slug or "unknown",
            "name": slug or str(cid),
            "ecosystem": "evm",
        }
    return None


def _funder_hints_for_hops(
    origins: EdgeCallResult,
    wallet: str,
    tier: str,
    ranked: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hints = origins.body.get("funder_hints")
    if isinstance(hints, list) and hints:
        return [h for h in hints if isinstance(h, dict)]
    top = origins.body.get("top_funders") or _module(origins).get("top_funders") or []
    n = HOP_FUNDER_N.get(tier, 2)
    out: list[dict[str, Any]] = []
    for row in (top if isinstance(top, list) else [])[:n]:
        if not isinstance(row, dict):
            continue
        addr = str(row.get("address") or "").lower()
        if not addr:
            continue
        chain = ranked[0] if ranked else None
        out.append({
            "address": addr,
            "weight": row.get("weight"),
            "chain_id": chain.get("chain_id") if chain else None,
            "ankr_slug": chain.get("ankr_slug") if chain else None,
        })
    return out


def _hop_entry_from_funder_risk(
    res: EdgeCallResult,
    *,
    address: str,
    weight: Any,
    hop: int,
    via: str | None = None,
) -> dict[str, Any]:
    if not res.ok:
        entry = {
            "address": address,
            "weight": weight,
            "hop": hop,
            "error": res.body.get("error") or f"http_{res.status}",
        }
        if via:
            entry["via"] = via
        return entry
    entry = {
        "address": address,
        "weight": weight,
        "hop": hop,
        "grade": res.body.get("grade"),
        "signals": res.body.get("signals") or {},
        "is_normal_wallet": bool(res.body.get("is_normal_wallet")),
        "module": res.body.get("module") or {
            "version": "funder-risk-v1",
            "signals": res.body.get("signals"),
            "grade": res.body.get("grade"),
        },
        "top_funders": res.body.get("top_funders") or [],
        "chain_id": res.body.get("chain_id"),
        "ankr_slug": res.body.get("ankr_slug"),
    }
    if res.body.get("skipped"):
        entry["skipped"] = True
        entry["skip_reason"] = res.body.get("skip_reason")
        entry["cex_name"] = res.body.get("cex_name")
    if via:
        entry["via"] = via
    return entry


def _run_funder_risk_hops(
    *,
    wallet: str,
    tier: str,
    origins: EdgeCallResult,
    ranked: list[dict[str, Any]],
    label_map: dict[str, dict[str, Any]],
    sb: Any,
    allow_hop2: bool,
) -> tuple[list[dict[str, Any]], list[Any], list[Any]]:
    """Hop-1 funder_risk screens; Experta hop-2 only when hop-1 is a normal wallet."""
    hop_results: list[dict[str, Any]] = []
    hop_labels: list[Any] = []
    soft_errors: list[Any] = []
    hints = _funder_hints_for_hops(origins, wallet, tier, ranked)
    hop1_for_hop2: list[dict[str, Any]] = []

    for hint in hints:
        addr = str(hint.get("address") or "").lower()
        if not addr or addr == ZERO_EVM_ADDRESS or addr == wallet:
            continue
        weight = hint.get("weight")
        skip = _cex_skip_info(addr, label_map=label_map, sb=sb)
        if skip:
            hop_results.append({"address": addr, "weight": weight, "hop": 1, **skip})
            soft_errors.append({
                "stage": "hops",
                "address": addr,
                "error": skip["skip_reason"],
                "cex_name": skip.get("cex_name"),
            })
            continue
        chain = _chain_from_hint(hint, ranked)
        if not chain:
            err = "missing_dominant_chain"
            hop_results.append({"address": addr, "weight": weight, "hop": 1, "error": err})
            soft_errors.append({"stage": "hops", "address": addr, "error": err})
            continue
        res = run_funder_risk(
            addr, chain, weight=weight, hop=1, subject=wallet, tier=tier
        )
        entry = _hop_entry_from_funder_risk(res, address=addr, weight=weight, hop=1)
        hop_results.append(entry)
        labels = res.body.get("interaction_labels") if res.ok else None
        if isinstance(labels, list):
            hop_labels.extend(labels)
            label_map.update(_labels_by_address(labels))
        if entry.get("error"):
            soft_errors.append({"stage": "hops", "address": addr, "error": entry["error"]})
        elif entry.get("skipped"):
            soft_errors.append({
                "stage": "hops",
                "address": addr,
                "error": entry.get("skip_reason") or "skipped",
                "cex_name": entry.get("cex_name"),
            })
        elif allow_hop2 and entry.get("is_normal_wallet"):
            hop1_for_hop2.append({
                "address": addr,
                "chain": {
                    "chain_id": entry.get("chain_id") if entry.get("chain_id") is not None else chain.get("chain_id"),
                    "ankr_slug": entry.get("ankr_slug") or chain.get("ankr_slug"),
                    "name": chain.get("name"),
                    "ecosystem": chain.get("ecosystem") or "evm",
                },
                "top_funders": entry.get("top_funders") or [],
            })
        sleep_ms(400)

    if allow_hop2:
        for h1 in hop1_for_hop2:
            via = h1["address"]
            chain = h1["chain"]
            for funder2 in (h1.get("top_funders") or [])[:2]:
                if not isinstance(funder2, dict):
                    continue
                addr2 = str(funder2.get("address") or "").lower()
                weight2 = funder2.get("weight")
                skip2 = _hop2_target_skip(addr2, subject=wallet, label_map=label_map, sb=sb)
                if skip2:
                    hop_results.append({
                        "address": addr2,
                        "weight": weight2,
                        "hop": 2,
                        "via": via,
                        **skip2,
                    })
                    soft_errors.append({
                        "stage": "hops",
                        "address": addr2,
                        "error": skip2["skip_reason"],
                        "cex_name": skip2.get("cex_name"),
                    })
                    continue
                res2 = run_funder_risk(
                    addr2, chain, weight=weight2, hop=2, subject=wallet, tier=tier
                )
                entry2 = _hop_entry_from_funder_risk(
                    res2, address=addr2, weight=weight2, hop=2, via=via
                )
                hop_results.append(entry2)
                labels2 = res2.body.get("interaction_labels") if res2.ok else None
                if isinstance(labels2, list):
                    hop_labels.extend(labels2)
                    label_map.update(_labels_by_address(labels2))
                if entry2.get("error"):
                    soft_errors.append({
                        "stage": "hops",
                        "address": addr2,
                        "error": entry2["error"],
                    })
                elif entry2.get("skipped"):
                    soft_errors.append({
                        "stage": "hops",
                        "address": addr2,
                        "error": entry2.get("skip_reason") or "skipped",
                        "cex_name": entry2.get("cex_name"),
                    })
                sleep_ms(400)

    return hop_results, hop_labels, soft_errors


def _run_origins_hop(
    address: str,
    chains: list[Any],
    hop: int,
    weight: Any,
) -> dict[str, Any]:
    """Legacy wrapper unused by new hops; kept for tests that may patch it."""
    hop_res = run_origins_partitioned(address, _normalize_chains(chains), "experta")
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
    in_weight = cp.get("in_weight")
    out_weight = cp.get("out_weight")
    base = {
        "address": addr,
        "weight": weight,
        "in_weight": in_weight,
        "out_weight": out_weight,
        "tier": "basica",
        "compliance_screen": False,
    }
    try:
        mc_loader = call_edge(
            "multichain-basica",
            {"address": addr, "tier": "basica", "include_upstream": True},
            timeout_ms=60_000,
            label=f"light-mc:{addr[:10]}",
        )
        if not mc_loader.ok:
            return {
                **base,
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
                **base,
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
                **base,
                "error": _err(origins, "origins"),
            }
        if not activity.ok:
            return {
                **base,
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
                **base,
                "error": _err(synth, "synthesize"),
            }
        return {
            **base,
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
            **base,
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
            {"address": wallet, "preview": False, "verify_signature": True, "mode": "multi"},
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
            "delivery_warnings": False,
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
        origins = run_origins_partitioned(wallet, _normalize_chains(ranked), "experta")
        soft_errors_early: list[Any] = list(origins.body.get("soft_errors") or [])
        if not origins.ok:
            err = _err(origins, "origins")
            soft_errors_early.append({"stage": "origins", "error": err})
            origins = EdgeCallResult(
                ok=True,
                status=origins.status,
                body={
                    "module": _soft_module_stub(stage="origins", error=err, top_key="top_funders"),
                    "top_funders": [],
                    "interaction_labels": [],
                    "tx_evidence": [],
                    "chain_alerts": [],
                    "soft_failed": True,
                },
            )
    with stage(sb, request_id, STAGE_ACTIVITY):
        activity = run_activity_partitioned(wallet, _normalize_chains(ranked), "experta")
        soft_errors_early.extend(list(activity.body.get("soft_errors") or []))
        if not activity.ok:
            err = _err(activity, "activity")
            soft_errors_early.append({"stage": "activity", "error": err})
            activity = EdgeCallResult(
                ok=True,
                status=activity.status,
                body={
                    "module": _soft_module_stub(
                        stage="activity", error=err, top_key="top_counterparties"
                    ),
                    "top_counterparties": [],
                    "interaction_labels": [],
                    "tx_evidence": [],
                    "chain_alerts": [],
                    "soft_failed": True,
                },
            )

    origins_mod = _module(origins)
    activity_mod = _module(activity)
    top_funders = origins.body.get("top_funders") or origins_mod.get("top_funders") or []
    if not isinstance(top_funders, list):
        top_funders = []
    hop_n = HOP_FUNDER_N["experta"]
    top_cps = activity.body.get("top_counterparties") or activity_mod.get("top_counterparties") or []
    if not isinstance(top_cps, list):
        top_cps = []

    label_map = _labels_by_address(origins.body.get("interaction_labels"))
    label_map.update(_labels_by_address(activity.body.get("interaction_labels")))

    soft_errors: list[Any] = list(soft_errors_early)
    with stage(sb, request_id, STAGE_HOPS):
        hop_results, hop_labels, hop_errs = _run_funder_risk_hops(
            wallet=wallet,
            tier="experta",
            origins=origins,
            ranked=_normalize_chains(ranked),
            label_map=label_map,
            sb=sb,
            allow_hop2=True,
        )
        soft_errors.extend(hop_errs)
    hop_tx: list[Any] = []

    light_targets = [cp for cp in top_cps[:5] if isinstance(cp, dict)]
    light_results: list[dict[str, Any]] = []
    with stage(sb, request_id, STAGE_LIGHTS):
        ran_light = False
        for cp in light_targets:
            addr = str(cp.get("address") or "").lower()
            skip = _cex_skip_info(addr, label_map=label_map, sb=sb)
            if skip:
                light_results.append({
                    "address": addr,
                    "weight": cp.get("weight"),
                    "in_weight": cp.get("in_weight"),
                    "out_weight": cp.get("out_weight"),
                    "tier": "basica",
                    "compliance_screen": False,
                    **skip,
                })
                soft_errors.append({
                    "stage": "lights",
                    "address": addr,
                    "error": skip["skip_reason"],
                    "cex_name": skip.get("cex_name"),
                })
                continue
            if ran_light:
                sleep_ms(1000)
            light = _run_basica_light(cp)
            ran_light = True
            light_results.append(light)
            if light.get("error"):
                soft_errors.append({
                    "stage": "lights",
                    "address": addr,
                    "error": light["error"],
                })

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
                    "hop_mode": "funder_risk",
                    "hop_funders": top_funders[:hop_n],
                    "activity_light": {
                        "n": 5,
                        "mode": "basica_embedded",
                        "compliance_screen": False,
                        "counterparties": light_targets,
                    },
                    "chains_ranked": ranked,
                    "multichain_coverage": mc_body.get("coverage"),
                    "ofac_layers": {
                        "A": "compliance-screen mode=multi (OFAC/UN/EU/HMT) wallet objetivo only",
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
        "upstream_errors": _merge_upstream_errors(synth.body.get("upstream_errors"), soft_errors),
        "compliance_column": synth.body.get("compliance_column"),
        "compliance_ok": bool(synth.body.get("compliance_ok")),
        "delivery_warnings": bool(soft_errors),
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
