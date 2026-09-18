"""Render riesgo-evaluacion-v1 envelope into branded PDF bytes (WeasyPrint)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from workers.analisis_pdf.i18n import Lang, normalize_idioma, t, tier_label

PACKAGE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PACKAGE_DIR / "assets"


def _format_observed(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        return text or "0"
    if isinstance(value, (int, str)):
        return str(value)
    return str(value)


def _format_condition(operador: Any, umbral: Any) -> str:
    op = str(operador or "").strip() or "?"
    if not isinstance(umbral, dict):
        return op
    parts: list[str] = []
    for key in ("valor", "min", "max", "eq", "gte", "lte", "gt", "lt"):
        if key in umbral and umbral[key] is not None:
            parts.append(f"{key}={umbral[key]}")
    if not parts:
        # fallback: compact json-ish
        for k, v in umbral.items():
            if v is not None:
                parts.append(f"{k}={v}")
    return f"{op} ({', '.join(parts)})" if parts else op


def _ambiente_key(raw: Any) -> str:
    text = str(raw or "").strip().lower()
    if text in {"sandbox"} or "sand" in text:
        return "sandbox"
    return "produccion"


def _ambiente_label(key: str, lang: Lang) -> str:
    if key == "sandbox":
        return t("riesgo_ambiente_sandbox", lang)
    return t("riesgo_ambiente_produccion", lang)


def _rule_row(regla: dict[str, Any]) -> dict[str, str]:
    return {
        "nombre": str(regla.get("nombre") or regla.get("codigo") or "—"),
        "codigo": str(regla.get("codigo") or regla.get("senal_codigo") or "—"),
        "observed": _format_observed(regla.get("valor_observado")),
        "condition": _format_condition(regla.get("operador"), regla.get("umbral")),
        "puntos": str(int(regla.get("puntos") or 0)),
    }


def _score_display(puntaje: Any, presupuesto: Any) -> str:
    try:
        p = int(puntaje or 0)
    except (TypeError, ValueError):
        p = 0
    try:
        b = int(presupuesto or 0)
    except (TypeError, ValueError):
        b = 0
    return f"{p} / {b}"


def _build_evaluation(ev: dict[str, Any], lang: Lang) -> dict[str, Any]:
    ambiente_key = _ambiente_key(ev.get("ambiente"))
    reglas = ev.get("reglas") if isinstance(ev.get("reglas"), list) else []
    matched: list[dict[str, str]] = []
    unmatched: list[dict[str, str]] = []
    for regla in reglas:
        if not isinstance(regla, dict):
            continue
        row = _rule_row(regla)
        if regla.get("matched"):
            matched.append(row)
        else:
            unmatched.append(row)

    version_num = ev.get("version_num")
    version_label = ""
    if version_num is not None and str(version_num).strip():
        version_label = f"{t('riesgo_version_label', lang)} {version_num}"

    nombre = str(ev.get("matriz_nombre") or ev.get("matriz_slug") or "—")
    return {
        "ambiente_key": ambiente_key,
        "ambiente_label": _ambiente_label(ambiente_key, lang),
        "matriz_nombre": nombre,
        "matriz_slug": str(ev.get("matriz_slug") or ""),
        "version_label": version_label,
        "score_display": _score_display(ev.get("puntaje"), ev.get("presupuesto_puntos")),
        "matched_rows": matched,
        "unmatched_rows": unmatched,
    }


def has_riesgo_evaluations(riesgo: Any) -> bool:
    if not isinstance(riesgo, dict):
        return False
    if riesgo.get("skipped_reason"):
        return False
    evaluations = riesgo.get("evaluations")
    return isinstance(evaluations, list) and len(evaluations) > 0


def build_riesgo_template_context(
    *,
    request_id: str,
    tier: str,
    wallet: str,
    riesgo: dict[str, Any],
    logo_uri: str | None = None,
    idioma: str | None = None,
) -> dict[str, Any]:
    lang = normalize_idioma(idioma)
    evaluations_in = riesgo.get("evaluations") if isinstance(riesgo.get("evaluations"), list) else []
    evaluations = [
        _build_evaluation(ev, lang)
        for ev in evaluations_in
        if isinstance(ev, dict)
    ]
    summary_cards = [
        {
            "ambiente_key": ev["ambiente_key"],
            "ambiente_label": ev["ambiente_label"],
            "matriz_nombre": ev["matriz_nombre"],
            "version_label": ev["version_label"],
            "score_display": ev["score_display"],
        }
        for ev in evaluations
    ]
    evaluated_at = str(riesgo.get("evaluated_at") or "").strip()

    return {
        "html_lang": lang,
        "page_title": t("riesgo_page_title", lang),
        "doc_title": t("riesgo_doc_title", lang),
        "wallet_label": t("wallet_label", lang),
        "evaluated_at_label": t("riesgo_evaluated_at_label", lang),
        "id_label": t("id_label", lang),
        "footer_wallet_label": t("footer_wallet_label", lang),
        "footer_date_label": t("footer_date_label", lang),
        "footer_created_by": t("riesgo_footer_created_by", lang),
        "footer_signals_disclaimer": t("footer_signals_disclaimer", lang),
        "summary_title": t("riesgo_summary_title", lang),
        "score_label": t("riesgo_score_label", lang),
        "version_label": t("riesgo_version_label", lang),
        "matched_title": t("riesgo_matched_title", lang),
        "unmatched_title": t("riesgo_unmatched_title", lang),
        "col_rule": t("riesgo_col_rule", lang),
        "col_codigo": t("riesgo_col_codigo", lang),
        "col_observed": t("riesgo_col_observed", lang),
        "col_condition": t("riesgo_col_condition", lang),
        "col_points": t("riesgo_col_points", lang),
        "no_matched": t("riesgo_no_matched", lang),
        "disclaimer": t("riesgo_disclaimer", lang),
        "logo_uri": logo_uri,
        "tier_label": tier_label(tier, lang),
        "wallet": wallet,
        "evaluated_at": evaluated_at,
        "request_id": request_id,
        "summary_cards": summary_cards,
        "evaluations": evaluations,
    }


def render_riesgo_html(context: dict[str, Any]) -> str:
    env = Environment(
        loader=FileSystemLoader(str(PACKAGE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("template_riesgo.html")
    return template.render(**context)


def _logo_uri() -> str | None:
    for name in ("pdf.jpg", "Lockup-Stacked.png", "Mono-White.png", "Lockup-Horizontal.png"):
        path = ASSETS_DIR / name
        if path.is_file():
            return path.as_uri()
    return None


def render_riesgo_pdf_bytes(
    *,
    request_id: str,
    tier: str,
    wallet: str,
    riesgo: dict[str, Any],
    idioma: str | None = None,
) -> bytes:
    """Render Motor de Riesgos PDF. Raises ImportError if WeasyPrint unavailable."""
    from weasyprint import CSS, HTML

    context = build_riesgo_template_context(
        request_id=request_id,
        tier=tier,
        wallet=wallet,
        riesgo=riesgo,
        logo_uri=_logo_uri(),
        idioma=idioma,
    )
    html = render_riesgo_html(context)
    base_url = PACKAGE_DIR.as_uri() + "/"
    document = HTML(string=html, base_url=base_url)
    stylesheets = [CSS(filename=str(PACKAGE_DIR / "styles.css"))]
    return document.write_pdf(stylesheets=stylesheets)
