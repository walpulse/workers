"""Render riesgo-evaluacion-v1 envelope into branded PDF bytes (WeasyPrint)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from workers.analisis_pdf.i18n import Lang, normalize_idioma, t, tier_label

PACKAGE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PACKAGE_DIR / "assets"

_EMPTY = "—"

_UMBRAL_NONE = frozenset({"is_true", "is_false", "is_null", "not_null"})
_UMBRAL_LIST = frozenset({"in", "not_in"})

_OP_I18N_KEYS: dict[str, str] = {
    "eq": "riesgo_op_eq",
    "neq": "riesgo_op_neq",
    "gt": "riesgo_op_gt",
    "gte": "riesgo_op_gte",
    "lt": "riesgo_op_lt",
    "lte": "riesgo_op_lte",
    "between": "riesgo_op_between",
    "in": "riesgo_op_in",
    "not_in": "riesgo_op_not_in",
    "is_true": "riesgo_op_is_true",
    "is_false": "riesgo_op_is_false",
    "is_null": "riesgo_op_is_null",
    "not_null": "riesgo_op_not_null",
}


def _display_or_dash(value: Any) -> str:
    if value is None:
        return _EMPTY
    text = str(value).strip()
    return text if text else _EMPTY


def _format_observed(value: Any) -> str:
    if value is None:
        return _EMPTY
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        return text or "0"
    if isinstance(value, (int, str)):
        return str(value)
    return str(value)


def _umbral_shape(operador: str) -> str:
    if operador in _UMBRAL_NONE:
        return "none"
    if operador == "between":
        return "range"
    if operador in _UMBRAL_LIST:
        return "list"
    return "single"


def _umbral_scalar(umbral: dict[str, Any]) -> Any:
    if "value" in umbral and umbral["value"] is not None:
        return umbral["value"]
    # Legacy key from early fixtures / envelopes.
    if "valor" in umbral and umbral["valor"] is not None:
        return umbral["valor"]
    return None


def _format_condition(operador: Any, umbral: Any, lang: Lang) -> str:
    op = str(operador or "").strip()
    op_key = _OP_I18N_KEYS.get(op)
    op_label = t(op_key, lang) if op_key else (op or "?")
    shape = _umbral_shape(op)
    if shape == "none":
        return op_label
    if not isinstance(umbral, dict):
        return op_label
    if shape == "range":
        lo = umbral.get("min", "?")
        hi = umbral.get("max", "?")
        return f"{op_label} {lo} – {hi}"
    if shape == "list":
        values = umbral.get("values")
        if isinstance(values, list) and values:
            joined = ", ".join(str(v) for v in values)
            return f"{op_label} {joined}"
        return op_label
    scalar = _umbral_scalar(umbral)
    if scalar is None:
        return op_label
    return f"{op_label} {_format_observed(scalar)}"


def _ambiente_key(raw: Any) -> str:
    text = str(raw or "").strip().lower()
    if text in {"sandbox"} or "sand" in text:
        return "sandbox"
    return "produccion"


def _ambiente_label(key: str, lang: Lang) -> str:
    if key == "sandbox":
        return t("riesgo_ambiente_sandbox", lang)
    return t("riesgo_ambiente_produccion", lang)


def _rule_row(regla: dict[str, Any], lang: Lang) -> dict[str, str]:
    return {
        "nombre": str(regla.get("nombre") or regla.get("codigo") or _EMPTY),
        "observed": _format_observed(regla.get("valor_observado")),
        "condition": _format_condition(regla.get("operador"), regla.get("umbral"), lang),
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


def _versions_by_id(enrichment: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(enrichment, dict):
        return {}
    versions = enrichment.get("versions")
    if not isinstance(versions, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for item in versions:
        if not isinstance(item, dict):
            continue
        vid = item.get("version_id")
        if vid is None:
            continue
        out[str(vid)] = item
    return out


def _build_evaluation(
    ev: dict[str, Any],
    lang: Lang,
    *,
    cliente_nombre: str,
    version_meta: dict[str, Any] | None,
) -> dict[str, Any]:
    ambiente_key = _ambiente_key(ev.get("ambiente"))
    reglas = ev.get("reglas") if isinstance(ev.get("reglas"), list) else []
    matched: list[dict[str, str]] = []
    unmatched: list[dict[str, str]] = []
    for regla in reglas:
        if not isinstance(regla, dict):
            continue
        row = _rule_row(regla, lang)
        if regla.get("matched"):
            matched.append(row)
        else:
            unmatched.append(row)

    meta = version_meta if isinstance(version_meta, dict) else {}
    version_num = ev.get("version_num")
    if version_num is None:
        version_num = meta.get("version_num")
    version_nombre = _display_or_dash(meta.get("nombre"))
    version_notas = _display_or_dash(meta.get("notas"))

    nombre = str(ev.get("matriz_nombre") or ev.get("matriz_slug") or _EMPTY)
    return {
        "ambiente_key": ambiente_key,
        "ambiente_label": _ambiente_label(ambiente_key, lang),
        "cliente_nombre": cliente_nombre or _EMPTY,
        "matriz_nombre": nombre,
        "version_num": _display_or_dash(version_num),
        "version_nombre": version_nombre,
        "version_notas": version_notas,
        "score_display": _score_display(ev.get("puntaje"), ev.get("presupuesto_puntos")),
        "matched_rows": matched,
        "unmatched_rows": unmatched,
        "identity_rows": [
            {"label": t("riesgo_label_cliente", lang), "value": cliente_nombre or _EMPTY},
            {"label": t("riesgo_label_ambiente", lang), "value": _ambiente_label(ambiente_key, lang)},
            {"label": t("riesgo_label_matriz", lang), "value": nombre},
            {"label": t("riesgo_version_label", lang), "value": _display_or_dash(version_num)},
            {"label": t("riesgo_version_nombre_label", lang), "value": version_nombre},
            {"label": t("riesgo_version_notas_label", lang), "value": version_notas},
            {"label": t("riesgo_score_label", lang), "value": _score_display(ev.get("puntaje"), ev.get("presupuesto_puntos"))},
        ],
    }


def has_riesgo_evaluations(riesgo: Any) -> bool:
    if not isinstance(riesgo, dict):
        return False
    if riesgo.get("skipped_reason"):
        return False
    evaluations = riesgo.get("evaluations")
    return isinstance(evaluations, list) and len(evaluations) > 0


def collect_version_ids(riesgo: dict[str, Any]) -> list[str]:
    evaluations = riesgo.get("evaluations")
    if not isinstance(evaluations, list):
        return []
    seen: set[str] = set()
    out: list[str] = []
    for ev in evaluations:
        if not isinstance(ev, dict):
            continue
        vid = ev.get("version_id")
        if vid is None:
            continue
        key = str(vid).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def build_riesgo_template_context(
    *,
    request_id: str,
    tier: str,
    wallet: str,
    riesgo: dict[str, Any],
    logo_uri: str | None = None,
    idioma: str | None = None,
    enrichment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lang = normalize_idioma(idioma)
    cliente_nombre = ""
    if isinstance(enrichment, dict):
        cliente_nombre = str(enrichment.get("cliente_nombre") or "").strip()
    versions = _versions_by_id(enrichment)

    evaluations_in = riesgo.get("evaluations") if isinstance(riesgo.get("evaluations"), list) else []
    evaluations = [
        _build_evaluation(
            ev,
            lang,
            cliente_nombre=cliente_nombre,
            version_meta=versions.get(str(ev.get("version_id"))),
        )
        for ev in evaluations_in
        if isinstance(ev, dict)
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
        "matched_title": t("riesgo_matched_title", lang),
        "unmatched_title": t("riesgo_unmatched_title", lang),
        "col_rule": t("riesgo_col_rule", lang),
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
    enrichment: dict[str, Any] | None = None,
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
        enrichment=enrichment,
    )
    html = render_riesgo_html(context)
    base_url = PACKAGE_DIR.as_uri() + "/"
    document = HTML(string=html, base_url=base_url)
    stylesheets = [CSS(filename=str(PACKAGE_DIR / "styles.css"))]
    return document.write_pdf(stylesheets=stylesheets)
