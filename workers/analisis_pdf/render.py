"""Render analisis-v1 JSON into branded PDF bytes (WeasyPrint)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

PACKAGE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PACKAGE_DIR / "assets"
TIER_LABELS = {
    "estandar": "Estándar",
    "experta": "Experta",
    "basica": "Básica",
}
MODULE_ORDER = (
    ("origins", "Orígenes"),
    ("activity", "Actividad"),
    ("multichain", "Multichain"),
    ("portfolio", "Portafolio"),
)
MAX_SIGNAL_ROWS = 10

SIGNAL_LABELS_ES: dict[str, str] = {
    "hhi": "HHI",
    "hhi_usd": "HHI USD",
    "unique_senders": "Remitentes únicos",
    "unique_senders_sum": "Remitentes únicos (suma)",
    "unique_counterparties": "Contrapartes únicas",
    "unique_counterparties_sum": "Contrapartes únicas (suma)",
    "counterparty_hhi": "HHI contrapartes",
    "priced_coverage_pct": "Cobertura pricing %",
    "sanctions_hit": "Exposición sanciones",
    "sanctions_hit_any": "Exposición sanciones (cualquier)",
    "mixing_risk": "Riesgo mixing",
    "sourcify_verified_pct": "Sourcify verificado %",
    "spellbook_labeled_pct": "Spellbook etiquetado %",
    "unverified_contract_pct": "Contratos no verificados %",
    "active_chains_30d": "Chains activas 30d",
    "active_chains_90d": "Chains activas 90d",
    "total_chains_with_activity": "Chains con actividad",
    "activity_span_days": "Span de actividad (días)",
    "dormant_ratio": "Ratio dormidas",
    "footprint_span_hhi": "HHI footprint",
    "recency_days": "Recencia (días)",
    "consistency": "Consistencia",
    "wash_score": "Wash score",
    "bot_like_score": "Bot-like score",
    "ofac_exposure_pct_value": "Exposición OFAC % valor",
    "mixer_exposure_pct_value": "Exposición mixer % valor",
    "bridge_exposure_pct_value": "Exposición bridge % valor",
    "airdrop_exposure_pct_value": "Exposición airdrop % valor",
    "protocol_exposure_pct_value": "Exposición protocolo % valor",
    "credible_value_usd": "Valor credible USD",
    "usable_value_usd": "Valor usable USD",
    "liquid_ratio": "Ratio líquido",
    "holdings_hhi": "HHI holdings",
    "dust_pct": "Dust %",
    "chains_ok": "Chains OK",
    "grade": "Grade (señal)",
}


def _locale_text(value: Any, lang: str = "esp") -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        # analisis-v1 uses both esp/eng/por and es/en/pt
        preferred = {
            "esp": ("esp", "es", "eng", "en", "por", "pt"),
            "es": ("es", "esp", "en", "eng", "pt", "por"),
            "eng": ("eng", "en", "esp", "es", "por", "pt"),
            "en": ("en", "eng", "es", "esp", "pt", "por"),
        }.get(lang, ("esp", "es", "eng", "en", "por", "pt"))
        for key in preferred:
            text = value.get(key)
            if isinstance(text, str) and text.strip():
                return text.strip()
    return ""


def _format_signal_value(value: Any) -> str:
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if abs(value) >= 100 or value == 0:
            return f"{value:.2f}".rstrip("0").rstrip(".")
        return f"{value:.4f}".rstrip("0").rstrip(".")
    if value is None:
        return "n/d"
    return str(value)


def _signal_label(key: str) -> str:
    if key in SIGNAL_LABELS_ES:
        return SIGNAL_LABELS_ES[key]
    return key.replace("_", " ").strip().capitalize()


def _collect_signal_rows(mod: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    def add_flat(source: Any) -> None:
        if not isinstance(source, dict):
            return
        for key, value in source.items():
            if key in seen or key == "grade":
                continue
            if isinstance(value, (dict, list)):
                continue
            seen.add(key)
            rows.append({"label": _signal_label(str(key)), "value": _format_signal_value(value)})
            if len(rows) >= MAX_SIGNAL_ROWS:
                return

    add_flat(mod.get("highlights"))
    if len(rows) < MAX_SIGNAL_ROWS:
        add_flat(mod.get("signals"))
    return rows


def _module_narrative(mod: dict[str, Any]) -> str:
    for key in ("summary", "narrative", "narrativa", "grade_narrative"):
        if key in mod:
            text = _locale_text(mod.get(key), "es")
            if text:
                return text
    for key in ("narratives", "narrative_trilingual"):
        nested = mod.get(key)
        text = _locale_text(nested, "es")
        if text:
            return text
    grade = str(mod.get("grade") or "?")
    return f"Módulo calificado {grade}."


def _extract_modules(analisis: dict[str, Any]) -> list[dict[str, Any]]:
    modules_root = analisis.get("modules")
    if not isinstance(modules_root, dict):
        modules_root = {}

    out: list[dict[str, Any]] = []
    for key, label in MODULE_ORDER:
        mod = modules_root.get(key)
        if mod is None and key == "portfolio":
            mod = analisis.get("portfolio")
        if not isinstance(mod, dict):
            continue
        grade = str(mod.get("grade") or "").strip().upper()
        if not grade or grade == "NONE":
            continue
        if grade not in {"A", "B", "C", "D", "F"}:
            grade = "C"
        out.append(
            {
                "name": label,
                "grade": grade,
                "narrative": _module_narrative(mod),
                "signals": _collect_signal_rows(mod),
            }
        )
    return out


PINATA_GATEWAY = "https://gateway.pinata.cloud/ipfs"


def _ipfs_https(cid: str | None) -> str:
    if not cid:
        return ""
    return f"{PINATA_GATEWAY}/{cid.strip()}"


def _compliance_section(analisis: dict[str, Any]) -> dict[str, Any]:
    """Build Compliance screen OFAC card from analisis.compliance_screen."""
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
        return {
            "available": False,
            "title": "Compliance screen OFAC",
            "message": "No disponible" + (f" — {detail}" if detail else ""),
            "rows": [],
        }

    verdict = screen.get("verdict")
    sanctioned = screen.get("sanctioned")
    sig = screen.get("signature_verified")
    rows = [
        {"label": "Veredicto", "value": str(verdict) if verdict is not None else "n/d"},
        {"label": "Sancionado", "value": _format_signal_value(sanctioned) if sanctioned is not None else "n/d"},
        {
            "label": "Signature verified",
            "value": _format_signal_value(sig) if sig is not None else "n/d",
        },
    ]
    return {
        "available": True,
        "title": "Compliance screen OFAC",
        "message": "",
        "rows": rows,
    }


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
) -> dict[str, Any]:
    synthesis = analisis.get("synthesis") if isinstance(analisis.get("synthesis"), dict) else {}
    synthesis_grade = str(synthesis.get("grade") or analisis.get("grade") or "C").strip().upper()
    if synthesis_grade not in {"A", "B", "C", "D", "F"}:
        synthesis_grade = "C"

    synthesis_label = _locale_text(synthesis.get("grade_label"), "es")
    if not synthesis_label:
        synthesis_label = _locale_text(analisis.get("grade_label"), "es") or f"Calificación {synthesis_grade}"

    synthesis_summary = _locale_text(synthesis.get("summary"), "es")

    temporal = analisis.get("temporal_scope") if isinstance(analisis.get("temporal_scope"), dict) else {}
    applicable_as_of = temporal.get("applicable_as_of") or temporal.get("as_of")
    if applicable_as_of is not None:
        applicable_as_of = str(applicable_as_of).replace("T", " ")[:19]

    disclaimer = _locale_text(
        temporal.get("disclaimer") or temporal.get("disclaimers"),
        "es",
    )
    if not disclaimer:
        disclaimer = (
            "Este análisis es una señal point-in-time. "
            "No garantiza comportamiento futuro ni sustituye debida diligencia del receptor."
        )

    analisis_url = _ipfs_https(analisis_cid)
    evidencia_url = _ipfs_https(evidencia_cid)

    return {
        "logo_uri": logo_uri,
        "tier_label": TIER_LABELS.get(tier, tier),
        "wallet": wallet,
        "applicable_as_of": applicable_as_of,
        "synthesis_grade": synthesis_grade,
        "synthesis_label": synthesis_label,
        "synthesis_summary": synthesis_summary,
        "modules": _extract_modules(analisis),
        "compliance": _compliance_section(analisis),
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
) -> bytes:
    """Render branded PDF. Raises ImportError if WeasyPrint is unavailable."""
    from weasyprint import CSS, HTML

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
    )
    html = render_html(context)
    base_url = PACKAGE_DIR.as_uri() + "/"
    document = HTML(string=html, base_url=base_url)
    stylesheets = [CSS(filename=str(PACKAGE_DIR / "styles.css"))]
    return document.write_pdf(stylesheets=stylesheets)
