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
    ("origins", "Origins"),
    ("activity", "Activity"),
    ("multichain", "Multichain"),
    ("portfolio", "Portfolio"),
)


def _locale_text(value: Any, lang: str = "esp") -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in (lang, "esp", "eng", "por"):
            text = value.get(key)
            if isinstance(text, str) and text.strip():
                return text.strip()
    return str(value).strip()


def _module_narrative(mod: dict[str, Any]) -> str:
    for key in ("summary", "narrative", "narrativa", "grade_narrative"):
        if key in mod:
            text = _locale_text(mod.get(key))
            if text:
                return text
    for key in ("narratives", "narrative_trilingual"):
        nested = mod.get(key)
        text = _locale_text(nested)
        if text:
            return text
    grade = str(mod.get("grade") or "?")
    return f"Módulo calificado {grade}."


def _extract_modules(analisis: dict[str, Any]) -> list[dict[str, str]]:
    modules_root = analisis.get("modules")
    if not isinstance(modules_root, dict):
        modules_root = {}

    out: list[dict[str, str]] = []
    for key, label in MODULE_ORDER:
        mod = modules_root.get(key)
        if mod is None and key == "portfolio":
            # Some shapes put portfolio at top-level
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
            }
        )
    return out


def build_template_context(
    *,
    request_id: str,
    tier: str,
    wallet: str,
    analisis: dict[str, Any],
    data_hash: str | None,
    analisis_cid: str | None,
    logo_uri: str | None,
) -> dict[str, Any]:
    synthesis = analisis.get("synthesis") if isinstance(analisis.get("synthesis"), dict) else {}
    synthesis_grade = str(synthesis.get("grade") or analisis.get("grade") or "C").strip().upper()
    if synthesis_grade not in {"A", "B", "C", "D", "F"}:
        synthesis_grade = "C"

    synthesis_label = _locale_text(synthesis.get("grade_label"))
    if not synthesis_label:
        synthesis_label = _locale_text(analisis.get("grade_label")) or f"Calificación {synthesis_grade}"

    temporal = analisis.get("temporal_scope") if isinstance(analisis.get("temporal_scope"), dict) else {}
    applicable_as_of = temporal.get("applicable_as_of") or temporal.get("as_of")
    if applicable_as_of is not None:
        applicable_as_of = str(applicable_as_of).replace("T", " ")[:19]

    disclaimer = _locale_text(temporal.get("disclaimers") or temporal.get("disclaimer"))
    if not disclaimer and isinstance(temporal.get("validity"), str):
        disclaimer = (
            "Este análisis es una señal point-in-time. "
            "No garantiza comportamiento futuro ni sustituye debida diligencia del receptor."
        )

    return {
        "logo_uri": logo_uri,
        "tier_label": TIER_LABELS.get(tier, tier),
        "wallet": wallet,
        "applicable_as_of": applicable_as_of,
        "synthesis_grade": synthesis_grade,
        "synthesis_label": synthesis_label,
        "weights_version": synthesis.get("weights_version") or "",
        "modules": _extract_modules(analisis),
        "disclaimer": disclaimer,
        "request_id": request_id,
        "data_hash": data_hash or "",
        "analisis_cid": analisis_cid or "",
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
) -> bytes:
    """Render branded PDF. Raises ImportError if WeasyPrint is unavailable."""
    from weasyprint import CSS, HTML

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
        logo_uri=logo_uri,
    )
    html = render_html(context)
    base_url = PACKAGE_DIR.as_uri() + "/"
    document = HTML(string=html, base_url=base_url)
    stylesheets = [CSS(filename=str(PACKAGE_DIR / "styles.css"))]
    return document.write_pdf(stylesheets=stylesheets)
