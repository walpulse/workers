"""Render analisis-v1 JSON into branded PDF bytes (WeasyPrint)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from workers.analisis_pdf.i18n import (
    MODULE_ORDER,
    Lang,
    bool_text,
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


def _format_signal_value(value: Any, lang: Lang, *, key: str = "") -> str:
    if isinstance(value, bool):
        return bool_text(value, lang)
    if value is None:
        return t("na", lang)

    pct_like = key.endswith("_pct") or key.endswith("_pct_value") or key.endswith("_ratio")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        num = float(value)
        if pct_like and 0 <= num <= 1:
            pct = num * 100
            return f"{pct:.2f}".rstrip("0").rstrip(".") + "%"
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


def _hop_grade(raw: dict[str, Any]) -> str:
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


def _hop_summary(raw: dict[str, Any], lang: Lang) -> str:
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
    return f"{pct:.1f}".rstrip("0").rstrip(".") + "%"


def _hop_cards(items: Any, lang: Lang, *, show_hop: bool) -> list[dict[str, Any]]:
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
        hop_n = raw.get("hop")
        out.append(
            {
                "address": str(raw.get("address") or "").strip(),
                "grade": _hop_grade(raw),
                "summary": _hop_summary(raw, lang),
                "weight": _format_weight_display(weight_num, total),
                "hop": str(hop_n) if hop_n is not None and show_hop else "",
            }
        )
    return out


def _build_module_section(
    key: str,
    mod: dict[str, Any],
    lang: Lang,
) -> dict[str, Any] | None:
    grade = _normalize_grade(mod.get("grade"))
    if not grade or grade == "NONE":
        return None

    hops: list[dict[str, Any]] = []
    hops_title = ""
    if key == "origins":
        hops = _hop_cards(mod.get("hops"), lang, show_hop=True)
        if hops:
            hops_title = t("origins_hops_title", lang)
    elif key == "activity":
        hops = _hop_cards(mod.get("counterparties_light"), lang, show_hop=False)
        if hops:
            hops_title = t("activity_lights_title", lang)

    return {
        "key": key,
        "name": module_name(key, lang),
        "grade": grade,
        "narrative": _module_narrative(mod, lang),
        "signals": _collect_signal_rows(mod, lang),
        "hops_title": hops_title,
        "hops": hops,
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
        "overview_title": t("overview_title", lang),
        "hop_meta_hop": t("hop_label", lang),
        "hop_meta_grade": t("grade_label", lang),
        "hop_meta_weight": t("weight_share_label", lang),
        "footer_note": t("footer_note", lang),
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
