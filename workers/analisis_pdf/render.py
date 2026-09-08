"""Render analisis-v1 JSON into branded PDF bytes (WeasyPrint)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from workers.analisis_pdf.i18n import (
    ENTITY_CLASS_ORDER,
    MODULE_ORDER,
    Lang,
    bool_text,
    confidence_label,
    custody_class_label,
    data_providers,
    entity_class_label,
    module_name,
    normalize_idioma,
    signal_label,
    t,
    tier_label,
)

PACKAGE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PACKAGE_DIR / "assets"
PINATA_GATEWAY = "https://gateway.pinata.cloud/ipfs"
SKIP_SIGNAL_KEYS = frozenset({"grade", "version"})


def _locale_text(value: Any, lang: Lang) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        preferred = {
            "es": ("es", "esp", "en", "eng", "pt", "por"),
            "en": ("en", "eng", "es", "esp", "pt", "por"),
            "pt": ("pt", "por", "es", "esp", "en", "eng"),
        }.get(lang, ("es", "esp", "en", "eng", "pt", "por"))
        for key in preferred:
            text = value.get(key)
            if isinstance(text, str) and text.strip():
                return text.strip()
    return ""


def _format_money_usd(num: float) -> str:
    text = f"{num:.2f}".rstrip("0").rstrip(".")
    return f"${text}"


def _format_pct_display(num: float) -> str:
    """Format a percentage that may already be 0–100 or a 0–1 fraction."""
    if 0 <= num <= 1:
        pct = num * 100
    else:
        pct = num
    return f"{pct:.2f}".rstrip("0").rstrip(".") + "%"


def _format_signal_value(value: Any, lang: Lang, *, key: str = "") -> str:
    if isinstance(value, bool):
        return bool_text(value, lang)
    if value is None:
        return t("na", lang)

    key_l = key.lower()
    # e.g. liquid_usd, total_value_usd_credible (usd mid-key), not hhi_usd
    is_usd_money = "_usd" in key_l and "hhi" not in key_l
    is_count = key_l.endswith("_positions") or key_l.endswith("_count")
    absolute_metric = is_usd_money or is_count
    pct_like = (
        not absolute_metric
        and (
            key_l.endswith("_pct")
            or key_l.endswith("_pct_value")
            or key_l.endswith("_ratio")
            or key_l.endswith("_hhi")
            or key_l in {"hhi", "hhi_usd"}
            or "hhi" in key_l
        )
    )
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        num = float(value)
        if is_usd_money:
            return _format_money_usd(num)
        if is_count:
            return str(int(num)) if float(num).is_integer() else str(num)
        if pct_like:
            return _format_pct_display(num)
        if isinstance(value, int):
            return str(value)
        if abs(num) >= 100 or num == 0:
            return f"{num:.2f}".rstrip("0").rstrip(".")
        return f"{num:.4f}".rstrip("0").rstrip(".")
    return str(value)


def _collect_signal_rows(mod: dict[str, Any], lang: Lang) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    def add_flat(source: Any) -> None:
        if not isinstance(source, dict):
            return
        for key, value in source.items():
            if key in seen or key in SKIP_SIGNAL_KEYS:
                continue
            if isinstance(value, (dict, list)):
                continue
            seen.add(key)
            rows.append(
                {
                    "label": signal_label(str(key), lang),
                    "value": _format_signal_value(value, lang, key=str(key)),
                }
            )

    add_flat(mod.get("highlights"))
    add_flat(mod.get("signals"))
    return rows


def _module_narrative(mod: dict[str, Any], lang: Lang) -> str:
    for key in ("summary", "narrative", "narrativa", "grade_narrative"):
        if key in mod:
            text = _locale_text(mod.get(key), lang)
            if text:
                return text
    for key in ("narratives", "narrative_trilingual"):
        nested = mod.get(key)
        text = _locale_text(nested, lang)
        if text:
            return text
    grade = str(mod.get("grade") or "?")
    return t("module_fallback", lang, grade=grade)


def _normalize_grade(value: Any) -> str:
    grade = str(value or "").strip().upper()
    if grade in {"A", "B", "C", "D", "F"}:
        return grade
    return ""


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _hop_excluded(raw: dict[str, Any]) -> bool:
    return bool(raw.get("skipped") or raw.get("skip_reason"))


def _hop_signals(raw: dict[str, Any]) -> dict[str, Any]:
    signals = _as_dict(raw.get("signals"))
    if signals:
        return signals
    module = _as_dict(raw.get("module"))
    return _as_dict(module.get("signals"))


def _is_funder_risk_hop(raw: dict[str, Any]) -> bool:
    """True when hop is the slim funder_risk screen (not full Origins)."""
    module = _as_dict(raw.get("module"))
    version = str(module.get("version") or "").lower()
    if version.startswith("funder-risk"):
        return True
    signals = _hop_signals(raw)
    return any(
        key in signals
        for key in (
            "cex_hit",
            "mixer_hit",
            "bridge_hit",
            "primary_category",
            "entity_class",
            "weight_to_subject",
        )
    )


def _hop_grade(raw: dict[str, Any]) -> str:
    if _hop_excluded(raw):
        return "—"
    grade = _normalize_grade(raw.get("grade"))
    if grade:
        return grade
    module = _as_dict(raw.get("module"))
    grade = _normalize_grade(module.get("grade"))
    if grade:
        return grade
    analisis = _as_dict(raw.get("analisis"))
    synthesis = _as_dict(analisis.get("synthesis"))
    grade = _normalize_grade(synthesis.get("grade"))
    return grade or "—"


def _funder_risk_summary(raw: dict[str, Any], lang: Lang) -> str:
    signals = _hop_signals(raw)
    grade = _hop_grade(raw)
    hits: list[str] = []
    if signals.get("sanctions_hit"):
        hits.append(t("hop_flag_ofac", lang))
    if signals.get("mixer_hit") or signals.get("mixing_risk"):
        hits.append(t("hop_flag_mixer", lang))
    if signals.get("cex_hit"):
        cex = str(signals.get("cex_name") or raw.get("cex_name") or "").strip()
        if cex:
            hits.append(t("hop_flag_cex_named", lang, name=cex))
        else:
            hits.append(t("hop_flag_cex", lang))
    if signals.get("bridge_hit"):
        hits.append(t("hop_flag_bridge", lang))
    exposure = (
        t("hop_funder_hits", lang, hits=", ".join(hits))
        if hits
        else t("hop_funder_clean", lang)
    )
    primary = str(signals.get("primary_category") or signals.get("entity_class") or "").strip()
    category = entity_class_label(primary, lang) if primary else t("na", lang)
    return t(
        "hop_funder_summary",
        lang,
        grade=grade or "—",
        exposure=exposure,
        category=category,
    )


def _hop_flag_row(
    *,
    key: str,
    name: str,
    hit: bool,
    lang: Lang,
    detail: str = "",
) -> dict[str, Any]:
    state = t("yes", lang) if hit else t("no", lang)
    text = t("hop_flag_bool", lang, name=name, value=state)
    if hit and detail:
        text = t("hop_flag_bool_detail", lang, name=name, value=state, detail=detail)
    return {"key": key, "label": text, "hit": hit, "value": state}


def _hop_flags(raw: dict[str, Any], lang: Lang) -> list[dict[str, Any]]:
    """Four explicit yes/no risk flags for Origins hops (incl. CEX skips)."""
    signals = _hop_signals(raw)
    cex_name = str(signals.get("cex_name") or raw.get("cex_name") or "").strip()
    reason = str(raw.get("skip_reason") or "").lower()

    if _hop_excluded(raw):
        ofac = "ofac" in reason or "sanction" in reason
        mixer = "mixer" in reason
        bridge = "bridge" in reason
        cex = bool(cex_name) or "cex" in reason
        return [
            _hop_flag_row(key="ofac", name=t("hop_flag_ofac", lang), hit=ofac, lang=lang),
            _hop_flag_row(key="mixer", name=t("hop_flag_mixer", lang), hit=mixer, lang=lang),
            _hop_flag_row(
                key="cex",
                name=t("hop_flag_cex", lang),
                hit=cex,
                lang=lang,
                detail=cex_name,
            ),
            _hop_flag_row(
                key="bridge", name=t("hop_flag_bridge", lang), hit=bridge, lang=lang
            ),
        ]

    if not _is_funder_risk_hop(raw):
        return []

    cex_hit = bool(signals.get("cex_hit"))
    return [
        _hop_flag_row(
            key="ofac",
            name=t("hop_flag_ofac", lang),
            hit=bool(signals.get("sanctions_hit")),
            lang=lang,
        ),
        _hop_flag_row(
            key="mixer",
            name=t("hop_flag_mixer", lang),
            hit=bool(signals.get("mixer_hit") or signals.get("mixing_risk")),
            lang=lang,
        ),
        _hop_flag_row(
            key="cex",
            name=t("hop_flag_cex", lang),
            hit=cex_hit,
            lang=lang,
            detail=cex_name if cex_hit else "",
        ),
        _hop_flag_row(
            key="bridge",
            name=t("hop_flag_bridge", lang),
            hit=bool(signals.get("bridge_hit")),
            lang=lang,
        ),
    ]


def _hop_summary(raw: dict[str, Any], lang: Lang) -> str:
    if _hop_excluded(raw):
        reason = str(raw.get("skip_reason") or "skipped")
        cex = str(raw.get("cex_name") or "").strip()
        if cex:
            return t("hop_excluded_cex", lang, reason=reason, cex_name=cex)
        return t("hop_excluded", lang, reason=reason)
    if raw.get("error"):
        return t("hop_error", lang, error=str(raw.get("error")))
    if _is_funder_risk_hop(raw):
        return _funder_risk_summary(raw, lang)
    text = _locale_text(raw.get("summary"), lang)
    if text:
        return text
    module = _as_dict(raw.get("module"))
    text = _locale_text(module.get("summary"), lang)
    if text:
        return text
    analisis = _as_dict(raw.get("analisis"))
    synthesis = _as_dict(analisis.get("synthesis"))
    text = _locale_text(synthesis.get("summary"), lang)
    if text:
        return text
    return _locale_text(synthesis.get("grade_label"), lang)


def _parse_weight(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_weight_display(num: float | None, total: float) -> str:
    if num is None or total <= 0:
        return ""
    pct = (num / total) * 100
    if 0 < pct < 0.1:
        return "<0.1%"
    return f"{pct:.1f}".rstrip("0").rstrip(".") + "%"


def _short_addr(address: str) -> str:
    addr = address.strip()
    if len(addr) <= 14:
        return addr
    return f"{addr[:8]}…{addr[-4:]}"


def _hop_card(
    raw: dict[str, Any],
    lang: Lang,
    *,
    weight: str,
    tag: str,
    level: int,
    via: str = "",
    risk_flags: bool = False,
) -> dict[str, Any]:
    return {
        "tag": tag,
        "level": level,
        "address": str(raw.get("address") or "").strip(),
        "grade": _hop_grade(raw),
        "summary": _hop_summary(raw, lang),
        "weight": weight,
        "via": via,
        "via_short": _short_addr(via) if via else "",
        "flags": _hop_flags(raw, lang) if risk_flags else [],
        "funder_risk": risk_flags
        and (_is_funder_risk_hop(raw) or _hop_excluded(raw)),
    }


def _hop_cards_flat(items: Any, lang: Lang) -> list[dict[str, Any]]:
    """Flat cards with % relative to the whole list (activity lights)."""
    if not isinstance(items, list):
        return []

    parsed: list[tuple[dict[str, Any], float | None]] = []
    total = 0.0
    for raw in items:
        if not isinstance(raw, dict):
            continue
        address = str(raw.get("address") or "").strip()
        if not address:
            continue
        weight_num = _parse_weight(raw.get("weight"))
        if weight_num is not None and weight_num > 0:
            total += weight_num
        parsed.append((raw, weight_num))

    out: list[dict[str, Any]] = []
    for raw, weight_num in parsed:
        out.append(
            _hop_card(
                raw,
                lang,
                weight=_format_weight_display(weight_num, total),
                tag="",
                level=0,
            )
        )
    return out


def _addr_key(address: str) -> str:
    return address.strip().lower()


def _origins_hop_groups(items: Any, lang: Lang) -> list[dict[str, Any]]:
    """Branch Origins as Hop 1x then its Hop 2x children (linked by via)."""
    if not isinstance(items, list):
        return []

    hop1: list[tuple[dict[str, Any], float | None]] = []
    hop2: list[tuple[dict[str, Any], float | None]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        address = str(raw.get("address") or "").strip()
        if not address:
            continue
        try:
            level = int(raw.get("hop") or 1)
        except (TypeError, ValueError):
            level = 1
        weight_num = _parse_weight(raw.get("weight"))
        if level <= 1:
            hop1.append((raw, weight_num))
        else:
            hop2.append((raw, weight_num))

    hop1.sort(
        key=lambda row: row[1] if row[1] is not None else -1.0,
        reverse=True,
    )
    hop1_total = sum(w for _, w in hop1 if w is not None and w > 0)
    parent_keys = {_addr_key(str(raw.get("address") or "")) for raw, _ in hop1}

    children_by_parent: dict[str, list[tuple[dict[str, Any], float | None]]] = {}
    orphans: list[tuple[dict[str, Any], float | None]] = []
    for raw, weight_num in hop2:
        via = str(raw.get("via") or "").strip()
        via_key = _addr_key(via) if via else ""
        if via_key and via_key in parent_keys:
            children_by_parent.setdefault(via_key, []).append((raw, weight_num))
        else:
            orphans.append((raw, weight_num))

    for kids in children_by_parent.values():
        kids.sort(
            key=lambda row: row[1] if row[1] is not None else -1.0,
            reverse=True,
        )

    groups: list[dict[str, Any]] = []
    for idx, (raw, weight_num) in enumerate(hop1):
        letter = chr(ord("a") + idx) if idx < 26 else str(idx + 1)
        parent_addr = str(raw.get("address") or "").strip()
        parent_key = _addr_key(parent_addr)
        kids = children_by_parent.get(parent_key, [])
        kids_total = sum(w for _, w in kids if w is not None and w > 0)

        cards = [
            _hop_card(
                raw,
                lang,
                weight=_format_weight_display(weight_num, hop1_total),
                tag=f"Hop 1{letter}",
                level=1,
                risk_flags=True,
            )
        ]
        for child_i, (child_raw, child_w) in enumerate(kids):
            child_tag = f"Hop 2{letter}" if len(kids) == 1 else f"Hop 2{letter}.{child_i + 1}"
            via = str(child_raw.get("via") or "").strip()
            cards.append(
                _hop_card(
                    child_raw,
                    lang,
                    weight=_format_weight_display(child_w, kids_total),
                    tag=child_tag,
                    level=2,
                    via=via,
                    risk_flags=True,
                )
            )
        groups.append({"level": 1, "letter": letter, "title": "", "cards": cards})

    if orphans:
        orphan_total = sum(w for _, w in orphans if w is not None and w > 0)
        orphan_cards = []
        for orphan_i, (raw, weight_num) in enumerate(orphans):
            via = str(raw.get("via") or "").strip()
            tag = "Hop 2" if len(orphans) == 1 else f"Hop 2.{orphan_i + 1}"
            orphan_cards.append(
                _hop_card(
                    raw,
                    lang,
                    weight=_format_weight_display(weight_num, orphan_total),
                    tag=tag,
                    level=2,
                    via=via,
                    risk_flags=True,
                )
            )
        groups.append(
            {
                "level": 2,
                "letter": "",
                "title": t("hop_orphans_title", lang),
                "cards": orphan_cards,
            }
        )
    return groups


def _format_chain_ts(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    return text.replace("T", " ").replace("Z", "")[:19]


def _extract_main_chains(mod: dict[str, Any], lang: Lang) -> list[dict[str, str]]:
    signals = mod.get("signals")
    if not isinstance(signals, dict):
        return []
    raw_list = signals.get("main_chains")
    if not isinstance(raw_list, list):
        return []

    rows: list[tuple[str, str, str]] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("ankr_slug") or item.get("goldrush_name") or "").strip()
        if not name:
            continue
        last_raw = item.get("last_tx_at") or item.get("last_seen_at")
        last_tx = _format_chain_ts(last_raw) or t("na", lang)
        sort_key = str(last_raw or "")
        rows.append((sort_key, name, last_tx))

    rows.sort(key=lambda r: r[0], reverse=True)
    return [{"name": name, "last_tx": last_tx} for _, name, last_tx in rows]


def _build_module_section(
    key: str,
    mod: dict[str, Any],
    lang: Lang,
) -> dict[str, Any] | None:
    grade = _normalize_grade(mod.get("grade"))
    if not grade or grade == "NONE":
        return None

    hop_groups: list[dict[str, Any]] = []
    hops_title = ""
    hops_blurb = ""
    if key == "origins":
        hop_groups = _origins_hop_groups(mod.get("hops"), lang)
        if hop_groups:
            hops_title = t("origins_hops_title", lang)
            hops_blurb = t("origins_hops_blurb", lang)
    elif key == "activity":
        cards = _hop_cards_flat(mod.get("counterparties_light"), lang)
        if cards:
            hops_title = t("activity_lights_title", lang)
            hop_groups = [{"level": 0, "title": "", "cards": cards}]

    chains = _extract_main_chains(mod, lang) if key == "multichain" else []
    clusters = _origin_clusters_section(mod, lang) if key == "origins" else None

    return {
        "key": key,
        "name": module_name(key, lang),
        "grade": grade,
        "narrative": _module_narrative(mod, lang),
        "signals": _collect_signal_rows(mod, lang),
        "hops_title": hops_title,
        "hops_blurb": hops_blurb,
        "hop_groups": hop_groups,
        "chains": chains,
        "chains_title": t("chains_section_title", lang) if chains else "",
        "chain_col_name": t("chain_col_name", lang),
        "chain_col_last_tx": t("chain_col_last_tx", lang),
        "clusters": clusters,
    }


def _extract_modules(analisis: dict[str, Any], lang: Lang) -> dict[str, dict[str, Any]]:
    modules_root = analisis.get("modules")
    if not isinstance(modules_root, dict):
        modules_root = {}

    by_key: dict[str, dict[str, Any]] = {}
    for key in MODULE_ORDER:
        mod = modules_root.get(key)
        if mod is None and key == "portfolio":
            mod = analisis.get("portfolio")
        if not isinstance(mod, dict):
            continue
        section = _build_module_section(key, mod, lang)
        if section:
            by_key[key] = section
    return by_key


def _overview_modules(modules_by_key: dict[str, dict[str, Any]], lang: Lang) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for key in MODULE_ORDER:
        section = modules_by_key.get(key)
        if section:
            out.append({"key": key, "name": section["name"], "grade": section["grade"]})
        else:
            out.append({"key": key, "name": module_name(key, lang), "grade": "—"})
    return out


def _ipfs_https(cid: str | None) -> str:
    if not cid:
        return ""
    return f"{PINATA_GATEWAY}/{cid.strip()}"


def _compliance_section(analisis: dict[str, Any], lang: Lang) -> dict[str, Any]:
    unavailable = bool(analisis.get("compliance_unavailable"))
    screen = analisis.get("compliance_screen")
    if not isinstance(screen, dict):
        screen = {}

    status = str(screen.get("status") or "").lower()
    if unavailable or status == "error" or not screen:
        detail = ""
        if isinstance(screen.get("error"), str):
            detail = screen["error"][:200]
        elif isinstance(screen.get("detail"), str):
            detail = screen["detail"][:200]
        message = t("unavailable", lang)
        if detail:
            message = f"{message} — {detail}"
        return {
            "available": False,
            "title": t("compliance_title", lang),
            "message": message,
            "rows": [],
        }

    verdict = screen.get("verdict")
    sanctioned = screen.get("sanctioned")
    sig = screen.get("signature_verified")
    rows = [
        {
            "label": t("verdict", lang),
            "value": str(verdict) if verdict is not None else t("na", lang),
        },
        {
            "label": t("sanctioned", lang),
            "value": (
                _format_signal_value(sanctioned, lang)
                if sanctioned is not None
                else t("na", lang)
            ),
        },
        {
            "label": t("signature_verified", lang),
            "value": _format_signal_value(sig, lang) if sig is not None else t("na", lang),
        },
    ]
    return {
        "available": True,
        "title": t("compliance_title", lang),
        "message": "",
        "rows": rows,
    }


def _format_custody_pct(value: Any, lang: Lang) -> str:
    if value is None:
        return t("na", lang)
    try:
        num = float(value)
    except (TypeError, ValueError):
        return t("na", lang)
    # Custody p_* are documented as 0–100.
    return f"{num:.2f}".rstrip("0").rstrip(".") + "%"


def _evidence_snippets(raw: Any, *, limit: int = 3) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if len(out) >= limit:
            break
        if isinstance(item, str) and item.strip():
            out.append(item.strip()[:160])
            continue
        if isinstance(item, dict):
            text = (
                item.get("summary")
                or item.get("detail")
                or item.get("message")
                or item.get("code")
                or item.get("layer")
            )
            if text is None:
                continue
            snippet = str(text).strip()
            if snippet:
                out.append(snippet[:160])
    return out


def _custody_section(analisis: dict[str, Any], lang: Lang) -> dict[str, Any] | None:
    raw = analisis.get("custody_classification")
    if not isinstance(raw, dict) or not raw:
        return None

    class_key = str(raw.get("class") or "").strip()
    confidence_key = str(raw.get("confidence") or "").strip().lower()
    subject = raw.get("subject") if isinstance(raw.get("subject"), dict) else {}

    rows: list[dict[str, str]] = [
        {
            "label": t("custody_class", lang),
            "value": custody_class_label(class_key, lang) if class_key else t("na", lang),
        },
        {
            "label": t("custody_p_hosted", lang),
            "value": _format_custody_pct(raw.get("p_hosted"), lang),
        },
        {
            "label": t("custody_p_unhosted", lang),
            "value": _format_custody_pct(raw.get("p_unhosted"), lang),
        },
        {
            "label": t("custody_p_unknown", lang),
            "value": _format_custody_pct(raw.get("p_unknown"), lang),
        },
    ]
    if confidence_key:
        rows.append(
            {
                "label": t("custody_confidence", lang),
                "value": confidence_label(confidence_key, lang),
            }
        )

    cex_name = subject.get("cex_name") or subject.get("distinct_name")
    if isinstance(cex_name, str) and cex_name.strip():
        rows.append({"label": t("custody_cex_name", lang), "value": cex_name.strip()})
    wallet_role = subject.get("wallet_role")
    if isinstance(wallet_role, str) and wallet_role.strip():
        rows.append({"label": t("custody_wallet_role", lang), "value": wallet_role.strip()})

    evidence = _evidence_snippets(raw.get("evidence"))
    disclaimer = _locale_text(raw.get("disclaimer"), lang) or t("custody_disclaimer", lang)

    return {
        "available": True,
        "title": t("custody_title", lang),
        "rows": rows,
        "evidence": evidence,
        "evidence_title": t("custody_evidence", lang) if evidence else "",
        "disclaimer": disclaimer,
    }


def _origin_clusters_section(mod: dict[str, Any], lang: Lang) -> dict[str, Any] | None:
    signals = mod.get("signals")
    if not isinstance(signals, dict):
        return None
    clusters = signals.get("origin_entity_clusters")
    if not isinstance(clusters, dict) or not clusters:
        return None

    pct_value = clusters.get("pct_value")
    if not isinstance(pct_value, dict):
        pct_value = {}

    rows: list[dict[str, str]] = []
    for class_key in ENTITY_CLASS_ORDER:
        if class_key not in pct_value:
            continue
        try:
            num = float(pct_value[class_key])
        except (TypeError, ValueError):
            continue
        if num == 0:
            continue
        rows.append(
            {
                "class_key": class_key,
                "label": entity_class_label(class_key, lang),
                "value": _format_pct_display(num),
            }
        )

    # Any extra buckets not in the canonical order
    for class_key, raw_pct in pct_value.items():
        if class_key in ENTITY_CLASS_ORDER:
            continue
        try:
            num = float(raw_pct)
        except (TypeError, ValueError):
            continue
        if num == 0:
            continue
        rows.append(
            {
                "class_key": str(class_key),
                "label": entity_class_label(str(class_key), lang),
                "value": _format_pct_display(num),
            }
        )

    top_raw = clusters.get("top_origins")
    top_origins: list[dict[str, str]] = []
    if isinstance(top_raw, list):
        for item in top_raw[:5]:
            if not isinstance(item, dict):
                continue
            address = str(item.get("address") or "").strip()
            if not address:
                continue
            entity = str(item.get("entity_class") or "").strip()
            label = str(item.get("label") or "").strip() or t("na", lang)
            try:
                pct_num = float(item.get("pct_value"))
                pct_text = _format_pct_display(pct_num)
            except (TypeError, ValueError):
                pct_text = t("na", lang)
            top_origins.append(
                {
                    "address": address,
                    "address_short": _short_addr(address),
                    "label": label,
                    "entity_class": entity_class_label(entity, lang) if entity else t("na", lang),
                    "pct": pct_text,
                }
            )

    if not rows and not top_origins:
        return None

    return {
        "title": t("clusters_title", lang),
        "col_class": t("clusters_col_class", lang),
        "col_pct": t("clusters_col_pct", lang),
        "col_address": t("clusters_col_address", lang),
        "col_label": t("clusters_col_label", lang),
        "top_title": t("clusters_top_title", lang),
        "rows": rows,
        "top_origins": top_origins,
    }


def _ipfs_help_html(analisis_url: str, evidencia_url: str, lang: Lang) -> str:
    def link(url: str) -> str:
        return f'<a class="ipfs-link" href="{url}">{url}</a>'

    if analisis_url and evidencia_url:
        return t(
            "ipfs_both",
            lang,
            analisis_link=link(analisis_url),
            evidencia_link=link(evidencia_url),
        )
    if analisis_url:
        return t("ipfs_analisis", lang, analisis_link=link(analisis_url))
    if evidencia_url:
        return t("ipfs_evidencia", lang, evidencia_link=link(evidencia_url))
    return ""


def build_template_context(
    *,
    request_id: str,
    tier: str,
    wallet: str,
    analisis: dict[str, Any],
    data_hash: str | None,
    analisis_cid: str | None,
    evidencia_cid: str | None,
    logo_uri: str | None,
    idioma: str | None = None,
) -> dict[str, Any]:
    lang = normalize_idioma(idioma)

    synthesis = analisis.get("synthesis") if isinstance(analisis.get("synthesis"), dict) else {}
    synthesis_grade = str(synthesis.get("grade") or analisis.get("grade") or "C").strip().upper()
    if synthesis_grade not in {"A", "B", "C", "D", "F"}:
        synthesis_grade = "C"

    synthesis_label = _locale_text(synthesis.get("grade_label"), lang)
    if not synthesis_label:
        synthesis_label = _locale_text(analisis.get("grade_label"), lang) or t(
            "synthesis_fallback", lang, grade=synthesis_grade
        )

    synthesis_summary = _locale_text(synthesis.get("summary"), lang)

    temporal = analisis.get("temporal_scope") if isinstance(analisis.get("temporal_scope"), dict) else {}
    applicable_as_of = temporal.get("applicable_as_of") or temporal.get("as_of")
    if applicable_as_of is not None:
        applicable_as_of = str(applicable_as_of).replace("T", " ")[:19]

    disclaimer = _locale_text(
        temporal.get("disclaimer") or temporal.get("disclaimers"),
        lang,
    )
    if not disclaimer:
        disclaimer = t("disclaimer_fallback", lang)

    analisis_url = _ipfs_https(analisis_cid)
    evidencia_url = _ipfs_https(evidencia_cid)
    modules_by_key = _extract_modules(analisis, lang)

    return {
        "html_lang": lang,
        "page_title": t("page_title", lang),
        "doc_title": t("doc_title", lang),
        "wallet_label": t("wallet_label", lang),
        "date_label": t("date_label", lang),
        "id_label": t("id_label", lang),
        "footer_wallet_label": t("footer_wallet_label", lang),
        "footer_date_label": t("footer_date_label", lang),
        "footer_created_by": t("footer_created_by", lang),
        "footer_signals_disclaimer": t("footer_signals_disclaimer", lang),
        "data_providers_title": t("data_providers_title", lang),
        "data_providers": data_providers(lang),
        "overview_title": t("overview_title", lang),
        "hop_meta_hop": t("hop_label", lang),
        "hop_meta_grade": t("grade_label", lang),
        "hop_meta_weight": t("weight_share_label", lang),
        "via_label": t("via_label", lang),
        "hop_flags_legend": t("hop_flags_legend", lang),
        "ipfs_help_html": _ipfs_help_html(analisis_url, evidencia_url, lang),
        "logo_uri": logo_uri,
        "tier_label": tier_label(tier, lang),
        "wallet": wallet,
        "applicable_as_of": applicable_as_of,
        "synthesis_grade": synthesis_grade,
        "synthesis_label": synthesis_label,
        "synthesis_summary": synthesis_summary,
        "overview_modules": _overview_modules(modules_by_key, lang),
        "mod_multichain": modules_by_key.get("multichain"),
        "mod_portfolio": modules_by_key.get("portfolio"),
        "mod_origins": modules_by_key.get("origins"),
        "mod_activity": modules_by_key.get("activity"),
        "compliance": _compliance_section(analisis, lang),
        "custody": _custody_section(analisis, lang),
        "disclaimer": disclaimer,
        "analisis_url": analisis_url,
        "evidencia_url": evidencia_url,
        "request_id": request_id,
        "data_hash": data_hash or "",
        "analisis_cid": analisis_cid or "",
        "evidencia_cid": evidencia_cid or "",
    }


def render_html(context: dict[str, Any]) -> str:
    env = Environment(
        loader=FileSystemLoader(str(PACKAGE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("template.html")
    return template.render(**context)


def render_pdf_bytes(
    *,
    request_id: str,
    tier: str,
    wallet: str,
    analisis: dict[str, Any],
    data_hash: str | None = None,
    analisis_cid: str | None = None,
    evidencia_cid: str | None = None,
    idioma: str | None = None,
) -> bytes:
    """Render branded PDF. Raises ImportError if WeasyPrint is unavailable."""
    from weasyprint import CSS, HTML

    logo_path = ASSETS_DIR / "pdf.jpg"
    if not logo_path.is_file():
        logo_path = ASSETS_DIR / "Lockup-Stacked.png"
    if not logo_path.is_file():
        logo_path = ASSETS_DIR / "Mono-White.png"
    if not logo_path.is_file():
        logo_path = ASSETS_DIR / "Lockup-Horizontal.png"
    logo_uri = logo_path.as_uri() if logo_path.is_file() else None

    context = build_template_context(
        request_id=request_id,
        tier=tier,
        wallet=wallet,
        analisis=analisis,
        data_hash=data_hash,
        analisis_cid=analisis_cid,
        evidencia_cid=evidencia_cid,
        logo_uri=logo_uri,
        idioma=idioma,
    )
    html = render_html(context)
    base_url = PACKAGE_DIR.as_uri() + "/"
    document = HTML(string=html, base_url=base_url)
    stylesheets = [CSS(filename=str(PACKAGE_DIR / "styles.css"))]
    return document.write_pdf(stylesheets=stylesheets)
