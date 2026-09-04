"""Tests for analisis_pdf render + pinata helpers."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from workers.analisis_pdf.i18n import SIGNAL_LABELS
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
            "hops": [
                {
                    "address": "0x1111111111111111111111111111111111111111",
                    "hop": 1,
                    "weight": 25,
                    "grade": "C",
                    "summary": {
                        "esp": "Fondeador hop 1 aceptable.",
                        "eng": "Hop 1 funder acceptable.",
                    },
                },
                {
                    "address": "0x3333333333333333333333333333333333333333",
                    "hop": 1,
                    "weight": 75,
                    "grade": "B",
                    "summary": {"esp": "Fondeador mayor.", "eng": "Main funder."},
                },
            ],
        },
        "activity": {
            "grade": "A",
            "summary": {
                "esp": "Actividad calificada A (Excelente).",
                "eng": "Activity graded A.",
            },
            "highlights": {
                "unique_counterparties": 9,
                "sanctions_hit": False,
                "sourcify_verified_pct": 0.25,
                "counterparty_hhi": 0.5,
            },
            "signals": {
                "kleros_tagged_counterparty_pct": 0.1,
                "wash_score": 0.2,
                "bot_like_score": 0.05,
                "spellbook_labeled_pct": 0.3,
                "ofac_exposure_pct_value": 0,
                "mixer_exposure_pct_value": 0,
                "bridge_exposure_pct_value": 0.01,
                "airdrop_exposure_pct_value": 0,
                "protocol_exposure_pct_value": 0.4,
                "organic_vs_synthetic": 0.7,
                "window_days": 90,
                "contract_interactions_total": 42,
            },
            "counterparties_light": [
                {
                    "address": "0x2222222222222222222222222222222222222222",
                    "weight": 99.1,
                    "tier": "basica",
                    "grade": "D",
                    "summary": {
                        "esp": "Contraparte top débil.",
                        "eng": "Weak top counterparty.",
                    },
                }
            ],
        },
        "multichain": {
            "grade": "C",
            "summary": {"esp": "Multichain calificado C (Aceptable).", "eng": "Multichain graded C."},
            "highlights": {"active_chains_90d": 2},
        },
        "portfolio": {
            "grade": "B",
            "summary": {"esp": "Portafolio calificado B (Bueno).", "eng": "Portfolio graded B."},
            "highlights": {
                "credible_value_usd": 15.17,
                "liquid_ratio": 1,
                "dust_ratio": 0.073,
            },
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
        idioma="es",
    )
    assert ctx["html_lang"] == "es"
    assert ctx["tier_label"] == "Estándar"
    assert ctx["mod_origins"]["name"] == "Orígenes"
    assert ctx["disclaimer"] == "Este análisis refleja señales on-chain en la fecha indicada."
    assert ctx["compliance"]["available"] is True
    assert ctx["compliance"]["title"] == "Compliance screen OFAC"
    labels = {r["label"] for r in ctx["compliance"]["rows"]}
    assert "Veredicto" in labels
    assert "Sancionado" in labels
    assert "Firma verificada" in labels
    assert ctx["analisis_url"] == "https://gateway.pinata.cloud/ipfs/QmAnalisis"
    assert ctx["evidencia_url"] == "https://gateway.pinata.cloud/ipfs/QmEvidencia"
    assert ctx["synthesis_label"] == "Bueno"
    assert "Lectura global B" in ctx["synthesis_summary"]
    assert len(ctx["overview_modules"]) == 4


def test_build_template_context_en():
    ctx = build_template_context(
        request_id="11111111-1111-1111-1111-111111111111",
        tier="experta",
        wallet="0xabc",
        analisis=FIXTURE,
        data_hash=None,
        analisis_cid="QmA",
        evidencia_cid="QmE",
        logo_uri=None,
        idioma="en",
    )
    assert ctx["html_lang"] == "en"
    assert ctx["doc_title"] == "Wallet analysis"
    assert ctx["wallet_label"] == "ANALYZED WALLET:"
    assert ctx["tier_label"] == "Expert"
    assert ctx["mod_origins"]["name"] == "Origins"
    assert ctx["synthesis_label"] == "Good"
    assert "Overall reading B" in ctx["synthesis_summary"]
    assert "Funding origin graded B." in ctx["mod_origins"]["narrative"]
    signal_labels = {r["label"] for r in ctx["mod_activity"]["signals"]}
    assert "Kleros-tagged counterparties" in signal_labels
    assert "Sourcify verified" in signal_labels


def test_compliance_unavailable():
    analisis = {
        **FIXTURE,
        "compliance_unavailable": True,
        "compliance_screen": {"status": "error", "error": "timeout"},
    }
    ctx = build_template_context(
        request_id="11111111-1111-1111-1111-111111111111",
        tier="estandar",
        wallet="0xabc",
        analisis=analisis,
        data_hash=None,
        analisis_cid=None,
        evidencia_cid=None,
        logo_uri=None,
        idioma="es",
    )
    assert ctx["compliance"]["available"] is False
    assert "No disponible" in ctx["compliance"]["message"]


def test_all_activity_signals_and_localized_labels():
    ctx = build_template_context(
        request_id="11111111-1111-1111-1111-111111111111",
        tier="experta",
        wallet="0xabc",
        analisis=FIXTURE,
        data_hash="0xdead",
        analisis_cid="QmAnalisis",
        evidencia_cid="QmEvidencia",
        logo_uri=None,
        idioma="es",
    )
    activity = ctx["mod_activity"]
    labels = [r["label"] for r in activity["signals"]]
    values_by_label = {r["label"]: r["value"] for r in activity["signals"]}
    assert "Contrapartes etiquetadas Kleros" in labels
    assert "Sourcify verificado" in labels
    assert "Puntaje wash" in labels
    assert len(activity["signals"]) >= 15
    assert values_by_label["Sourcify verificado"] == "25%"
    assert "_" not in "".join(labels)


def test_hops_weight_share_and_grade():
    ctx = build_template_context(
        request_id="11111111-1111-1111-1111-111111111111",
        tier="experta",
        wallet="0xabc",
        analisis=FIXTURE,
        data_hash=None,
        analisis_cid=None,
        evidencia_cid=None,
        logo_uri=None,
        idioma="es",
    )
    origins = ctx["mod_origins"]
    activity = ctx["mod_activity"]
    assert origins["hops_title"] == "Hops / fondeadores analizados"
    assert origins["hops"][0]["hop"] == "1"
    assert origins["hops"][0]["grade"] == "C"
    assert origins["hops"][0]["weight"] == "25%"
    assert origins["hops"][1]["weight"] == "75%"
    assert "~" not in origins["hops"][0]["weight"]
    assert "e+" not in origins["hops"][0]["weight"].lower()
    assert "Fondeador hop 1" in origins["hops"][0]["summary"]
    assert activity["hops_title"] == "Contrapartes top analizadas"
    assert activity["hops"][0]["grade"] == "D"
    assert activity["hops"][0]["weight"] == "100%"
    assert "Contraparte top débil" in activity["hops"][0]["summary"]


def test_legacy_nested_hop_and_light_grades():
    analisis = copy.deepcopy(FIXTURE)
    analisis["modules"]["origins"]["hops"] = [
        {
            "address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "hop": 1,
            "weight": 6.37e21,
            "module": {
                "grade": "D",
                "summary": {"esp": "Hop legacy D.", "eng": "Legacy hop D."},
            },
        },
        {
            "address": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "hop": 2,
            "weight": 6.37e21,
            "module": {
                "grade": "C",
                "summary": {"esp": "Hop legacy C.", "eng": "Legacy hop C."},
            },
        },
    ]
    analisis["modules"]["activity"]["counterparties_light"] = [
        {
            "address": "0xcccccccccccccccccccccccccccccccccccccccc",
            "weight": 1e21,
            "analisis": {
                "synthesis": {
                    "grade": "F",
                    "summary": {"esp": "Light legacy F.", "eng": "Legacy light F."},
                }
            },
        }
    ]
    ctx = build_template_context(
        request_id="11111111-1111-1111-1111-111111111111",
        tier="experta",
        wallet="0xabc",
        analisis=analisis,
        data_hash=None,
        analisis_cid=None,
        evidencia_cid=None,
        logo_uri=None,
        idioma="es",
    )
    assert ctx["mod_origins"]["hops"][0]["grade"] == "D"
    assert "Hop legacy D" in ctx["mod_origins"]["hops"][0]["summary"]
    assert ctx["mod_origins"]["hops"][0]["weight"] == "50%"
    assert "~" not in ctx["mod_origins"]["hops"][0]["weight"]
    assert ctx["mod_activity"]["hops"][0]["grade"] == "F"
    assert "Light legacy F" in ctx["mod_activity"]["hops"][0]["summary"]
    assert ctx["mod_activity"]["hops"][0]["weight"] == "100%"


def test_page_layout_order():
    ctx = build_template_context(
        request_id="11111111-1111-1111-1111-111111111111",
        tier="experta",
        wallet="0xabc",
        analisis=FIXTURE,
        data_hash="0xdead",
        analisis_cid="QmAnalisis",
        evidencia_cid="QmEvidencia",
        logo_uri=None,
        idioma="es",
    )
    html = render_html(ctx)
    assert 'class="page page-1"' in html
    assert 'class="page page-break page-2"' in html
    assert 'class="page page-break page-3"' in html
    assert 'class="page page-break page-4"' in html
    assert "Vista general" in html
    assert 'class="overview-grid"' in html

    i1 = html.index('class="page page-1"')
    i2 = html.index('class="page page-break page-2"')
    i3 = html.index('class="page page-break page-3"')
    i4 = html.index('class="page page-break page-4"')
    assert i1 < i2 < i3 < i4

    page1 = html[i1:i2]
    page2 = html[i2:i3]
    page3 = html[i3:i4]
    page4 = html[i4:]
    assert "Vista general" in page1
    assert "Compliance screen OFAC" in page1
    assert 'class="module-name display">Multichain</h3>' in page1
    assert "disclaimer" not in page1.lower() or "class=\"disclaimer\"" not in page1
    assert 'class="disclaimer"' not in page1
    assert "ipfs-help" not in page1
    assert 'class="module-name display">Portafolio</h3>' in page2
    assert 'class="module-name display">' in page3
    assert "Hops / fondeadores" in page3
    assert "Actividad" in page4
    assert "Contrapartes top" in page4
    assert 'class="disclaimer"' in page4
    assert "ipfs-help" in page4
    assert "request_id" in page4


def test_ratio_signals_as_percent():
    ctx = build_template_context(
        request_id="11111111-1111-1111-1111-111111111111",
        tier="experta",
        wallet="0xabc",
        analisis=FIXTURE,
        data_hash=None,
        analisis_cid=None,
        evidencia_cid=None,
        logo_uri=None,
        idioma="es",
    )
    by_label = {r["label"]: r["value"] for r in ctx["mod_portfolio"]["signals"]}
    assert by_label["Ratio líquido"] == "100%"
    assert by_label["Ratio dust"] == "7.3%"


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
        idioma="es",
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
    assert "Hops / fondeadores analizados" in html
    assert "Contrapartes top analizadas" in html
    assert "Contrapartes etiquetadas Kleros" in html
    assert "kleros_tagged" not in html
    for match in re.findall(r'class="signal-label">([^<]+)<', html):
        assert "_" not in match


def test_signal_catalog_covers_fixture_keys():
    activity = FIXTURE["modules"]["activity"]
    keys = set(activity["highlights"]) | set(activity["signals"])
    keys -= {"nested"}
    missing = [k for k in keys if k not in SIGNAL_LABELS]
    assert missing == []


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
            idioma="es",
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
