"""Tests for analisis_pdf render + pinata helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from workers.analisis_pdf.pinata import _auth_attempts, pin_pdf_to_pinata
from workers.analisis_pdf.render import build_template_context, render_html, render_pdf_bytes

FIXTURE = {
    "version": "analisis-v1",
    "temporal_scope": {
        "applicable_as_of": "2026-09-03T12:00:00Z",
        "validity": "point_in_time",
        "disclaimer": {
            "es": "Este análisis refleja señales on-chain en la fecha indicada.",
            "en": "This analysis reflects on-chain signals at the stated date.",
            "pt": "Esta análise reflete sinais on-chain na data indicada.",
        },
    },
    "compliance_screen": {
        "status": "ok",
        "verdict": "clean",
        "sanctioned": False,
        "signature_verified": True,
        "provider": "nsgoods",
    },
    "modules": {
        "origins": {
            "grade": "B",
            "summary": {
                "esp": "Origen de fondos calificado B (Bueno).",
                "eng": "Funding origin graded B.",
            },
            "highlights": {"hhi_usd": 0.42, "unique_senders": 3},
            "signals": {"priced_coverage_pct": 80, "nested": {"x": 1}},
        },
        "activity": {
            "grade": "A",
            "summary": {"esp": "Actividad calificada A (Excelente)."},
            "highlights": {"unique_counterparties": 9, "sanctions_hit": False},
        },
        "multichain": {
            "grade": "C",
            "summary": {"esp": "Multichain calificado C (Aceptable)."},
            "highlights": {"active_chains_90d": 2},
        },
        "portfolio": {
            "grade": "B",
            "summary": {"esp": "Portafolio calificado B (Bueno)."},
            "highlights": {"credible_value_usd": 15.17},
        },
    },
    "synthesis": {
        "grade": "B",
        "grade_label": {"esp": "Bueno", "eng": "Good"},
        "weights_version": "synthesis-v1-estandar",
        "summary": {
            "esp": "Lectura global B (Bueno): en conjunto la wallet luce sólida como contraparte.",
            "eng": "Overall reading B (Good): the wallet looks solid as a counterparty.",
        },
    },
}


def test_build_template_context_es():
    ctx = build_template_context(
        request_id="11111111-1111-1111-1111-111111111111",
        tier="estandar",
        wallet="0xabc",
        analisis=FIXTURE,
        data_hash="0xdead",
        analisis_cid="QmAnalisis",
        evidencia_cid="QmEvidencia",
        logo_uri=None,
    )
    assert ctx["tier_label"] == "Estándar"
    assert ctx["modules"][0]["name"] == "Orígenes"
    assert ctx["disclaimer"] == "Este análisis refleja señales on-chain en la fecha indicada."
    assert ctx["compliance"]["available"] is True
    assert ctx["compliance"]["title"] == "Compliance screen OFAC"
    labels = {r["label"] for r in ctx["compliance"]["rows"]}
    assert "Veredicto" in labels
    assert "Sancionado" in labels
    assert "Signature verified" in labels
    assert ctx["analisis_url"] == "https://gateway.pinata.cloud/ipfs/QmAnalisis"
    assert ctx["evidencia_url"] == "https://gateway.pinata.cloud/ipfs/QmEvidencia"
    assert ctx["synthesis_label"] == "Bueno"
    assert "Lectura global B" in ctx["synthesis_summary"]
    assert "weights_version" not in ctx


def test_compliance_unavailable():
    analisis = {**FIXTURE, "compliance_unavailable": True, "compliance_screen": {"status": "error", "error": "timeout"}}
    ctx = build_template_context(
        request_id="11111111-1111-1111-1111-111111111111",
        tier="estandar",
        wallet="0xabc",
        analisis=analisis,
        data_hash=None,
        analisis_cid=None,
        evidencia_cid=None,
        logo_uri=None,
    )
    assert ctx["compliance"]["available"] is False
    assert "No disponible" in ctx["compliance"]["message"]


def test_render_html_layout_copy():
    ctx = build_template_context(
        request_id="11111111-1111-1111-1111-111111111111",
        tier="experta",
        wallet="0xabc",
        analisis=FIXTURE,
        data_hash="0xdead",
        analisis_cid="QmAnalisis",
        evidencia_cid="QmEvidencia",
        logo_uri=None,
    )
    html = render_html(ctx)
    assert "Análisis de wallet" in html
    assert "Señales on-chain" not in html
    assert "WALLET ANALIZADA:" in html
    assert "FECHA ANALISIS:" in html
    assert "Compliance screen OFAC" in html
    assert "Veredicto" in html
    assert "Sancionado" in html
    assert "gateway.pinata.cloud/ipfs/QmAnalisis" in html
    assert "gateway.pinata.cloud/ipfs/QmEvidencia" in html
    assert "mayor información sobre este análisis" in html
    assert "constatar la información usada" in html
    assert "Síntesis " not in html
    assert "synthesis-v1-" not in html
    assert "Bueno" in html
    assert "Lectura global B (Bueno)" in html


def test_render_pdf_bytes_smoke():
    try:
        import weasyprint  # noqa: F401
    except (ImportError, OSError):
        pytest.skip("weasyprint unavailable")
    try:
        pdf = render_pdf_bytes(
            request_id="11111111-1111-1111-1111-111111111111",
            tier="estandar",
            wallet="0x475f589bd4bfe82b333b8006dcc278f393b8e124",
            analisis=FIXTURE,
            data_hash="0xabc",
            analisis_cid="QmAbc",
            evidencia_cid="QmEvid",
        )
    except OSError as e:
        pytest.skip(f"weasyprint system libs missing: {e}")
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1000


def test_auth_attempts_prefer_jwt(monkeypatch):
    monkeypatch.setenv("PINATA_JWT", "jwt-token")
    monkeypatch.setenv("PINATA_API_KEY", "k")
    monkeypatch.setenv("PINATA_API_SECRET", "s")
    attempts = _auth_attempts()
    assert attempts[0][0] == "jwt"
    assert attempts[1][0] == "api_key"


def test_pin_pdf_to_pinata_uses_jwt(monkeypatch):
    monkeypatch.setenv("PINATA_JWT", "jwt-token")
    monkeypatch.delenv("PINATA_API_KEY", raising=False)
    monkeypatch.delenv("PINATA_API_SECRET", raising=False)

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"IpfsHash": "QmPinnedPdf"}).encode()

    with patch("workers.analisis_pdf.pinata.urllib.request.urlopen", return_value=FakeResp()):
        cid = pin_pdf_to_pinata(b"%PDF-1.4 fake", request_id="req-1")
    assert cid == "QmPinnedPdf"


def test_assets_present():
    assets = Path(__file__).resolve().parents[1] / "workers" / "analisis_pdf" / "assets"
    assert (assets / "pdf.jpg").is_file()
    fonts = assets / "fonts"
    assert (fonts / "Inter-Regular.ttf").is_file()
    assert (fonts / "JetBrainsMono-Regular.ttf").is_file()
