"""i18n subject + HTML/text bodies for analisis_email."""

from __future__ import annotations

from html import escape
from typing import Any, Literal

Lang = Literal["es", "en", "pt"]

PINATA_GATEWAY = "https://gateway.pinata.cloud/ipfs"

_SUBJECT = {
    "es": "Tu análisis Walpulse está listo",
    "en": "Your Walpulse analysis is ready",
    "pt": "Sua análise Walpulse está pronta",
}

_INTRO = {
    "es": "El PDF de tu análisis de wallet ya está disponible.",
    "en": "The PDF for your wallet analysis is ready.",
    "pt": "O PDF da sua análise de carteira já está disponível.",
}

_CTA = {
    "es": "Abrir PDF",
    "en": "Open PDF",
    "pt": "Abrir PDF",
}

_LABELS = {
    "request_id": {"es": "Identificación", "en": "Request ID", "pt": "Identificação"},
    "wallet": {"es": "Wallet", "en": "Wallet", "pt": "Carteira"},
    "tier": {"es": "Tier", "en": "Tier", "pt": "Nível"},
    "grade": {"es": "Síntesis", "en": "Synthesis", "pt": "Síntese"},
    "analisis": {"es": "JSON análisis (IPFS)", "en": "Analysis JSON (IPFS)", "pt": "JSON análise (IPFS)"},
    "evidencia": {"es": "JSON evidencia (IPFS)", "en": "Evidence JSON (IPFS)", "pt": "JSON evidência (IPFS)"},
}

_DISCLAIMER = {
    "es": (
        "Walpulse produce señales on-chain de reputación. "
        "El receptor interpreta las señales; no es screening oficial ni decisión de compliance."
    ),
    "en": (
        "Walpulse produces on-chain reputation signals. "
        "The recipient interprets them; this is not official screening or a compliance decision."
    ),
    "pt": (
        "Walpulse produz sinais on-chain de reputação. "
        "O receptor interpreta os sinais; não é screening oficial nem decisão de compliance."
    ),
}

_TIER_LABEL = {
    "estandar": {"es": "Estándar", "en": "Standard", "pt": "Padrão"},
    "experta": {"es": "Experta", "en": "Expert", "pt": "Expert"},
}


def normalize_lang(idioma: str | None) -> Lang:
    raw = (idioma or "es").strip().lower()
    if raw in ("es", "en", "pt"):
        return raw  # type: ignore[return-value]
    return "es"


def ipfs_url(cid: str | None) -> str | None:
    if not cid:
        return None
    c = str(cid).strip()
    if not c:
        return None
    return f"{PINATA_GATEWAY}/{c}"


def build_email(row: dict[str, Any]) -> dict[str, str]:
    lang = normalize_lang(row.get("idioma") if isinstance(row.get("idioma"), str) else None)
    request_id = str(row.get("id") or "")
    wallet = str(row.get("wallet") or "")
    tier_key = str(row.get("tier") or "")
    tier = _TIER_LABEL.get(tier_key, {}).get(lang, tier_key)
    grade = str(row.get("grade") or "").strip()
    grade_label = str(row.get("grade_label") or "").strip()
    grade_display = " ".join(x for x in (grade, grade_label) if x).strip() or "—"

    pdf_url = ipfs_url(row.get("pdf_cid") if isinstance(row.get("pdf_cid"), str) else None)
    if not pdf_url:
        raise ValueError("missing_pdf_cid")
    analisis_url = ipfs_url(
        row.get("analisis_cid") if isinstance(row.get("analisis_cid"), str) else None
    )
    evidencia_url = ipfs_url(
        row.get("evidencia_cid") if isinstance(row.get("evidencia_cid"), str) else None
    )

    subject = _SUBJECT[lang]
    intro = _INTRO[lang]
    cta = _CTA[lang]
    disc = _DISCLAIMER[lang]

    def lab(key: str) -> str:
        return _LABELS[key][lang]

    rows_html = [
        f"<tr><td><strong>{escape(lab('request_id'))}</strong></td><td><code>{escape(request_id)}</code></td></tr>",
        f"<tr><td><strong>{escape(lab('wallet'))}</strong></td><td><code>{escape(wallet)}</code></td></tr>",
        f"<tr><td><strong>{escape(lab('tier'))}</strong></td><td>{escape(tier)}</td></tr>",
        f"<tr><td><strong>{escape(lab('grade'))}</strong></td><td>{escape(grade_display)}</td></tr>",
    ]
    if analisis_url:
        rows_html.append(
            f"<tr><td><strong>{escape(lab('analisis'))}</strong></td>"
            f'<td><a href="{escape(analisis_url)}">{escape(analisis_url)}</a></td></tr>'
        )
    if evidencia_url:
        rows_html.append(
            f"<tr><td><strong>{escape(lab('evidencia'))}</strong></td>"
            f'<td><a href="{escape(evidencia_url)}">{escape(evidencia_url)}</a></td></tr>'
        )

    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<body style="font-family: system-ui, sans-serif; color: #111; line-height: 1.45;">
  <p>{escape(intro)}</p>
  <p><a href="{escape(pdf_url)}" style="display:inline-block;padding:10px 16px;background:#0ea5e9;color:#fff;text-decoration:none;border-radius:6px;">{escape(cta)}</a></p>
  <p><a href="{escape(pdf_url)}">{escape(pdf_url)}</a></p>
  <table style="border-collapse:collapse;margin:16px 0;">{''.join(rows_html)}</table>
  <p style="font-size:13px;color:#555;">{escape(disc)}</p>
  <p style="font-size:12px;color:#888;">Walpulse · <a href="https://www.walpulse.com">walpulse.com</a></p>
</body>
</html>
"""

    text_lines = [
        intro,
        "",
        f"{cta}: {pdf_url}",
        "",
        f"{lab('request_id')}: {request_id}",
        f"{lab('wallet')}: {wallet}",
        f"{lab('tier')}: {tier}",
        f"{lab('grade')}: {grade_display}",
    ]
    if analisis_url:
        text_lines.append(f"{lab('analisis')}: {analisis_url}")
    if evidencia_url:
        text_lines.append(f"{lab('evidencia')}: {evidencia_url}")
    text_lines.extend(["", disc, "", "Walpulse · https://www.walpulse.com"])
    text = "\n".join(text_lines)

    return {"subject": subject, "html": html, "text": text, "lang": lang, "pdf_url": pdf_url}
