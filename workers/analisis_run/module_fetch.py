"""Per-chain fetch with partition (same coverage) + Edge score/aggregate."""

from __future__ import annotations

import sys
import time
from typing import Any

from workers.analisis_run.edge_client import EdgeCallResult, call_edge

ORIGINS_TX_CAP = {"estandar": 250, "experta": 500, "basica": 100}
ACTIVITY_WINDOW_DAYS = {"estandar": 45, "experta": 90, "basica": 15}

_INITIAL_ORIGINS_SLICE = 100
_MIN_ORIGINS_SLICE = 25
_INITIAL_ACTIVITY_CHUNK = 75
_MIN_ACTIVITY_CHUNK = 25
_MS_DAY = 86_400_000


def _log(msg: str) -> None:
    """Progress lines for GHA (flush so they appear before the step ends)."""
    print(msg, flush=True)
    sys.stdout.flush()


def _chain_tag(chain: dict[str, Any]) -> str:
    cid = chain.get("chain_id")
    slug = chain.get("ankr_slug") or chain.get("name") or "?"
    return f"{cid}/{slug}"


def _tx_key(tx: dict[str, Any]) -> str:
    return (
        f"{tx.get('hash')}:{tx.get('category')}:{tx.get('contract') or ''}:"
        f"{tx.get('direction')}"
    )


def _merge_txs(into: list[dict[str, Any]], more: Any, *, cap: int | None = None) -> int:
    if not isinstance(more, list):
        return 0
    seen = {_tx_key(t) for t in into if isinstance(t, dict)}
    gained = 0
    for raw in more:
        if not isinstance(raw, dict):
            continue
        k = _tx_key(raw)
        if k in seen:
            continue
        seen.add(k)
        into.append(raw)
        gained += 1
        if cap is not None and len(into) >= cap:
            break
    return gained


def _merge_labels(into: list[Any], more: Any) -> None:
    if isinstance(more, list):
        into.extend(more)


def fetch_origins_chain_partitioned(
    wallet: str,
    chain: dict[str, Any],
    tier: str,
) -> dict[str, Any]:
    """Accumulate inflows up to tier cap via fetch_slice; halve slice on failure."""
    target = ORIGINS_TX_CAP.get(tier, 250)
    tag = _chain_tag(chain)
    inflows: list[dict[str, Any]] = []
    labels: list[Any] = []
    evidence: list[Any] = []
    after_ms: int | None = None
    slice_size = _INITIAL_ORIGINS_SLICE
    attempts: list[str] = []
    _log(f"origins chain={tag} start target={target}")

    while len(inflows) < target:
        remaining = target - len(inflows)
        attempt = min(slice_size, remaining)
        progressed = False
        while attempt >= _MIN_ORIGINS_SLICE:
            body: dict[str, Any] = {
                "mode": "fetch_slice",
                "address": wallet,
                "chain": chain,
                "tier": tier,
                "origins_tx_cap": attempt,
            }
            if after_ms is not None:
                body["after_ms"] = after_ms
            _log(
                f"origins chain={tag} slice_cap={attempt} "
                f"fetched={len(inflows)}/{target} after_ms={after_ms}"
            )
            res = call_edge(
                "analisis-origins",
                body,
                timeout_ms=120_000,
                max_attempts=2,
                label=f"origins-slice:{chain.get('chain_id')}:{attempt}",
            )
            if res.ok:
                gained = _merge_txs(
                    inflows, res.body.get("inflows") or res.body.get("transfers"), cap=target
                )
                _merge_labels(labels, res.body.get("interaction_labels"))
                if res.body.get("tx_evidence") is not None:
                    evidence.append(res.body["tx_evidence"])
                attempts.append(f"ok+{gained}@{attempt}")
                progressed = True
                slice_size = _INITIAL_ORIGINS_SLICE
                has_more = bool(res.body.get("has_more"))
                nxt = res.body.get("next_cursor") if isinstance(res.body.get("next_cursor"), dict) else None
                _log(
                    f"origins chain={tag} slice_ok +{gained} "
                    f"total={len(inflows)}/{target} has_more={has_more}"
                )
                if not has_more or not nxt or nxt.get("after_ms") is None:
                    _log(f"origins chain={tag} done fetched={len(inflows)}/{target}")
                    return {
                        "ok": True,
                        "chain": chain,
                        "inflows": inflows,
                        "interaction_labels": labels,
                        "tx_evidence": evidence,
                        "chain_alert": {
                            "chain_id": chain.get("chain_id"),
                            "ankr_slug": chain.get("ankr_slug"),
                            "module": "origins",
                            "status": "chunked" if len(attempts) > 1 else "ok",
                            "fetched": len(inflows),
                            "cap": target,
                            "attempts": attempts,
                        },
                    }
                after_ms = int(nxt["after_ms"])
                break
            err = res.body.get("error") or res.status
            attempts.append(f"fail@{attempt}:{err}")
            nxt_attempt = attempt // 2
            _log(f"origins chain={tag} slice_fail cap={attempt} err={err} → retry_cap={nxt_attempt}")
            attempt = nxt_attempt
        if not progressed:
            _log(f"origins chain={tag} excluded fetched={len(inflows)}/{target}")
            return {
                "ok": False,
                "chain": chain,
                "inflows": inflows,
                "interaction_labels": labels,
                "tx_evidence": evidence,
                "chain_alert": {
                    "chain_id": chain.get("chain_id"),
                    "ankr_slug": chain.get("ankr_slug"),
                    "module": "origins",
                    "status": "excluded",
                    "fetched": len(inflows),
                    "cap": target,
                    "attempts": attempts,
                    "error": attempts[-1] if attempts else "unreadable",
                },
            }

    _log(f"origins chain={tag} done fetched={min(len(inflows), target)}/{target} (cap)")
    return {
        "ok": True,
        "chain": chain,
        "inflows": inflows[:target],
        "interaction_labels": labels,
        "tx_evidence": evidence,
        "chain_alert": {
            "chain_id": chain.get("chain_id"),
            "ankr_slug": chain.get("ankr_slug"),
            "module": "origins",
            "status": "chunked",
            "fetched": min(len(inflows), target),
            "cap": target,
            "attempts": attempts,
        },
    }


def _split_day_segments(total_days: int) -> list[tuple[int, int]]:
    """Return (window_days, offset_days_from_now) pairs covering [0, total_days)."""
    if total_days <= 30:
        return [(total_days, 0)]
    parts = max(2, (total_days + 29) // 30)
    seg = total_days // parts
    rem = total_days - seg * parts
    out: list[tuple[int, int]] = []
    offset = 0
    for i in range(parts):
        length = seg + (1 if i < rem else 0)
        if length <= 0:
            continue
        out.append((offset + length, offset))
        offset += length
    return out


def _fetch_activity_segment(
    wallet: str,
    chain: dict[str, Any],
    tier: str,
    window_days: int,
    offset_days: int,
) -> dict[str, Any] | None:
    """Fetch one temporal segment with chunk partition. None = segment unreadable."""
    tag = _chain_tag(chain)
    txs: list[dict[str, Any]] = []
    labels: list[Any] = []
    evidence: list[Any] = []
    before_bound = int(time.time() * 1000) - offset_days * _MS_DAY if offset_days > 0 else None
    before_cursor: int | None = before_bound
    chunk = _INITIAL_ACTIVITY_CHUNK
    hard_cap = 5000
    _log(f"activity chain={tag} segment window_days={window_days} offset_days={offset_days}")

    while len(txs) < hard_cap:
        attempt = chunk
        progressed = False
        while attempt >= _MIN_ACTIVITY_CHUNK:
            body: dict[str, Any] = {
                "mode": "fetch_slice",
                "address": wallet,
                "chain": chain,
                "tier": tier,
                "window_days": window_days,
                "chunk_size": attempt,
            }
            if before_bound is not None:
                body["before_ms"] = before_bound
            if before_cursor is not None:
                body["before_ms_cursor"] = before_cursor
            _log(
                f"activity chain={tag} chunk={attempt} "
                f"txs={len(txs)} w={window_days} off={offset_days}"
            )
            res = call_edge(
                "analisis-activity",
                body,
                timeout_ms=120_000,
                max_attempts=2,
                label=f"activity-slice:{chain.get('chain_id')}:w{window_days}:{attempt}",
            )
            if res.ok:
                gained = _merge_txs(txs, res.body.get("transfers") or res.body.get("txs"), cap=hard_cap)
                _merge_labels(labels, res.body.get("interaction_labels"))
                if res.body.get("tx_evidence") is not None:
                    evidence.append(res.body["tx_evidence"])
                progressed = True
                chunk = _INITIAL_ACTIVITY_CHUNK
                has_more = bool(res.body.get("has_more"))
                nxt = res.body.get("next_cursor") if isinstance(res.body.get("next_cursor"), dict) else None
                _log(f"activity chain={tag} chunk_ok +{gained} total={len(txs)} has_more={has_more}")
                if not has_more or not nxt or nxt.get("before_ms") is None:
                    return {"txs": txs, "interaction_labels": labels, "tx_evidence": evidence}
                before_cursor = int(nxt["before_ms"])
                if gained == 0:
                    return {"txs": txs, "interaction_labels": labels, "tx_evidence": evidence}
                break
            err = res.body.get("error") or res.status
            nxt_attempt = attempt // 2
            _log(f"activity chain={tag} chunk_fail size={attempt} err={err} → retry={nxt_attempt}")
            attempt = nxt_attempt
        if not progressed:
            _log(f"activity chain={tag} segment_fail w={window_days} off={offset_days}")
            return None
    return {"txs": txs, "interaction_labels": labels, "tx_evidence": evidence}


def fetch_activity_chain_partitioned(
    wallet: str,
    chain: dict[str, Any],
    tier: str,
) -> dict[str, Any]:
    """Cover full tier window via temporal segments that sum to the same days."""
    target_days = ACTIVITY_WINDOW_DAYS.get(tier, 45)
    tag = _chain_tag(chain)
    plans: list[list[tuple[int, int]]] = [
        [(target_days, 0)],
        _split_day_segments(target_days),
    ]
    if target_days >= 45:
        fine: list[tuple[int, int]] = []
        offset = 0
        part = max(15, target_days // 6)
        while offset < target_days:
            length = min(part, target_days - offset)
            fine.append((offset + length, offset))
            offset += length
        plans.append(fine)

    last_err = "unreadable"
    _log(f"activity chain={tag} start target_days={target_days}")
    for plan_i, plan in enumerate(plans):
        _log(f"activity chain={tag} plan={plan_i + 1}/{len(plans)} segments={len(plan)}")
        txs: list[dict[str, Any]] = []
        labels: list[Any] = []
        evidence: list[Any] = []
        ok_all = True
        for window_days, offset in plan:
            seg = _fetch_activity_segment(wallet, chain, tier, window_days, offset)
            if seg is None:
                ok_all = False
                last_err = f"segment_fail:w{window_days}:off{offset}"
                break
            _merge_txs(txs, seg["txs"])
            _merge_labels(labels, seg["interaction_labels"])
            evidence.extend(seg.get("tx_evidence") or [])
        if ok_all:
            _log(
                f"activity chain={tag} done txs={len(txs)} "
                f"days={target_days} segments={len(plan)}"
            )
            return {
                "ok": True,
                "chain": chain,
                "txs": txs,
                "interaction_labels": labels,
                "tx_evidence": evidence,
                "window_days": target_days,
                "chain_alert": {
                    "chain_id": chain.get("chain_id"),
                    "ankr_slug": chain.get("ankr_slug"),
                    "module": "activity",
                    "status": "chunked" if len(plan) > 1 else "ok",
                    "window_days": target_days,
                    "target_window_days": target_days,
                    "fetched": len(txs),
                    "segments": len(plan),
                },
            }

    _log(f"activity chain={tag} excluded err={last_err}")
    return {
        "ok": False,
        "chain": chain,
        "txs": [],
        "interaction_labels": [],
        "tx_evidence": [],
        "window_days": target_days,
        "chain_alert": {
            "chain_id": chain.get("chain_id"),
            "ankr_slug": chain.get("ankr_slug"),
            "module": "activity",
            "status": "excluded",
            "window_days": target_days,
            "target_window_days": target_days,
            "error": last_err,
            "fetched": 0,
        },
    }


def run_origins_partitioned(wallet: str, chains: list[dict[str, Any]], tier: str) -> EdgeCallResult:
    packs: list[dict[str, Any]] = []
    soft: list[dict[str, Any]] = []
    n = len([c for c in chains if isinstance(c, dict)])
    _log(f"origins module start tier={tier} chains={n} wallet={wallet[:12]}…")
    for i, chain in enumerate(chains):
        if not isinstance(chain, dict):
            continue
        _log(f"origins module chain {i + 1}/{n} id={chain.get('chain_id')}")
        fetched = fetch_origins_chain_partitioned(wallet, chain, tier)
        if not fetched["ok"] and not fetched["inflows"]:
            soft.append({"stage": "origins", "chain_id": chain.get("chain_id"), "error": "excluded"})
            packs.append({
                "signals": {
                    "chain_id": chain.get("chain_id"),
                    "ankr_slug": chain.get("ankr_slug"),
                    "error": fetched["chain_alert"].get("error"),
                    "excluded": True,
                    "grade": None,
                },
                "tx_evidence": fetched.get("tx_evidence"),
                "interaction_labels": [],
                "inflows": [],
                "chain_alert": fetched.get("chain_alert"),
            })
            continue
        _log(f"origins score chain={_chain_tag(chain)} inflows={len(fetched['inflows'])}")
        scored = call_edge(
            "analisis-origins",
            {
                "mode": "score_from",
                "address": wallet,
                "chain": chain,
                "tier": tier,
                "inflows": fetched["inflows"],
            },
            timeout_ms=180_000,
            max_attempts=2,
            label=f"origins-score:{chain.get('chain_id')}",
        )
        if not scored.ok:
            soft.append({
                "stage": "origins",
                "chain_id": chain.get("chain_id"),
                "error": scored.body.get("error") or f"http_{scored.status}",
            })
            _log(
                f"origins score_fail chain={_chain_tag(chain)} "
                f"err={scored.body.get('error') or scored.status}"
            )
            packs.append({
                "signals": {
                    "chain_id": chain.get("chain_id"),
                    "ankr_slug": chain.get("ankr_slug"),
                    "error": scored.body.get("error") or f"http_{scored.status}",
                    "excluded": True,
                    "grade": None,
                },
                "tx_evidence": fetched.get("tx_evidence"),
                "interaction_labels": fetched.get("interaction_labels") or [],
                "inflows": fetched.get("inflows") or [],
                "chain_alert": {
                    **(fetched.get("chain_alert") or {}),
                    "status": "excluded",
                    "error": scored.body.get("error") or f"http_{scored.status}",
                },
            })
            continue
        packs.append({
            "signals": scored.body.get("signals") or {},
            "tx_evidence": scored.body.get("tx_evidence") or fetched.get("tx_evidence"),
            "interaction_labels": scored.body.get("interaction_labels")
            or fetched.get("interaction_labels")
            or [],
            "top_funders": scored.body.get("top_funders") or [],
            "inflows": scored.body.get("inflows") or fetched.get("inflows") or [],
            "chain_alert": fetched.get("chain_alert"),
        })

    usable = [p for p in packs if not (p.get("signals") or {}).get("excluded")]
    _log(f"origins aggregate packs={len(packs)} usable={len(usable)} soft={len(soft)}")
    if not usable:
        err = soft[0]["error"] if soft else "origins_no_chains"
        return EdgeCallResult(
            ok=False,
            status=504,
            body={"error": err, "packs": packs, "soft_errors": soft},
        )

    agg = call_edge(
        "analisis-origins",
        {"mode": "aggregate_from", "address": wallet, "tier": tier, "packs": packs},
        timeout_ms=60_000,
        max_attempts=2,
        label="origins-aggregate",
    )
    if not agg.ok:
        _log(f"origins aggregate_fail err={agg.body.get('error') or agg.status}")
        return agg
    body = dict(agg.body)
    body["soft_errors"] = soft
    _log("origins module done")
    return EdgeCallResult(ok=True, status=200, body=body)


def run_activity_partitioned(wallet: str, chains: list[dict[str, Any]], tier: str) -> EdgeCallResult:
    packs: list[dict[str, Any]] = []
    soft: list[dict[str, Any]] = []
    target_days = ACTIVITY_WINDOW_DAYS.get(tier, 45)
    n = len([c for c in chains if isinstance(c, dict)])
    _log(
        f"activity module start tier={tier} chains={n} "
        f"target_days={target_days} wallet={wallet[:12]}…"
    )
    for i, chain in enumerate(chains):
        if not isinstance(chain, dict):
            continue
        _log(f"activity module chain {i + 1}/{n} id={chain.get('chain_id')}")
        fetched = fetch_activity_chain_partitioned(wallet, chain, tier)
        if not fetched["ok"] and not fetched["txs"]:
            soft.append({"stage": "activity", "chain_id": chain.get("chain_id"), "error": "excluded"})
            packs.append({
                "signals": {
                    "chain_id": chain.get("chain_id"),
                    "ankr_slug": chain.get("ankr_slug"),
                    "error": fetched["chain_alert"].get("error"),
                    "excluded": True,
                    "grade": None,
                },
                "tx_evidence": fetched.get("tx_evidence"),
                "interaction_labels": [],
                "txs": [],
                "chain_alert": fetched.get("chain_alert"),
            })
            continue
        _log(f"activity score chain={_chain_tag(chain)} txs={len(fetched['txs'])}")
        scored = call_edge(
            "analisis-activity",
            {
                "mode": "score_from",
                "address": wallet,
                "chain": chain,
                "tier": tier,
                "txs": fetched["txs"],
                "window_days": target_days,
            },
            timeout_ms=180_000,
            max_attempts=2,
            label=f"activity-score:{chain.get('chain_id')}",
        )
        if not scored.ok:
            soft.append({
                "stage": "activity",
                "chain_id": chain.get("chain_id"),
                "error": scored.body.get("error") or f"http_{scored.status}",
            })
            _log(
                f"activity score_fail chain={_chain_tag(chain)} "
                f"err={scored.body.get('error') or scored.status}"
            )
            packs.append({
                "signals": {
                    "chain_id": chain.get("chain_id"),
                    "ankr_slug": chain.get("ankr_slug"),
                    "error": scored.body.get("error") or f"http_{scored.status}",
                    "excluded": True,
                    "grade": None,
                },
                "tx_evidence": fetched.get("tx_evidence"),
                "interaction_labels": fetched.get("interaction_labels") or [],
                "txs": fetched.get("txs") or [],
                "chain_alert": {
                    **(fetched.get("chain_alert") or {}),
                    "status": "excluded",
                },
            })
            continue
        packs.append({
            "signals": scored.body.get("signals") or {},
            "tx_evidence": scored.body.get("tx_evidence") or fetched.get("tx_evidence"),
            "interaction_labels": scored.body.get("interaction_labels")
            or fetched.get("interaction_labels")
            or [],
            "top_counterparties": scored.body.get("top_counterparties") or [],
            "txs": scored.body.get("txs") or fetched.get("txs") or [],
            "chain_alert": fetched.get("chain_alert"),
        })

    usable = [p for p in packs if not (p.get("signals") or {}).get("excluded")]
    _log(f"activity aggregate packs={len(packs)} usable={len(usable)} soft={len(soft)}")
    if not usable:
        err = soft[0]["error"] if soft else "activity_no_chains"
        return EdgeCallResult(
            ok=False,
            status=504,
            body={"error": err, "packs": packs, "soft_errors": soft},
        )

    agg = call_edge(
        "analisis-activity",
        {"mode": "aggregate_from", "address": wallet, "tier": tier, "packs": packs},
        timeout_ms=60_000,
        max_attempts=2,
        label="activity-aggregate",
    )
    if not agg.ok:
        _log(f"activity aggregate_fail err={agg.body.get('error') or agg.status}")
        return agg
    body = dict(agg.body)
    body["soft_errors"] = soft
    _log("activity module done")
    return EdgeCallResult(ok=True, status=200, body=body)
