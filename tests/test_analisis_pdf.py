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
    "custody_classification": {
        "version": "custody_classification_v1",
        "class": "likely_unhosted",
        "p_hosted": 18,
        "p_unhosted": 62,
        "p_unknown": 20,
        "confidence": "medium",
        "subject": {
            "cex_name": None,
            "distinct_name": None,
            "wallet_role": None,
            "is_protocol": False,
        },
        "evidence": [
            "No CEX catalog match for subject",
            "Behavior score favors personal EOA patterns",
        ],
        "disclaimer": {
            "esp": "Señal on-chain; no prueba control de claves.",
            "eng": "On-chain signal; does not prove key control.",
            "por": "Sinal on-chain; não prova controle de chaves.",
        },
    },
    "modules": {
        "origins": {
            "grade": "B",
            "summary": {
                "esp": "Origen de fondos calificado B (Bueno).",
                "eng": "Funding origin graded B.",
            },
            "highlights": {"hhi_usd": 0.42, "unique_senders": 3},
            "signals": {
                "priced_coverage_pct": 80,
                "cex_deposit_inferred_pct": 0.12,
                "cex_curated_pct": 0.35,
                "origin_entity_clusters": {
                    "version": "origin-entity-clusters-v1",
                    "pct_value": {
                        "exchange_vasp": 35,
                        "exchange_deposit_inferred": 12,
                        "defi_protocol": 10,
                        "mixer": 0,
                        "sanctioned": 0,
                        "bridge": 8,
                        "airdrop": 5,
                        "unlabeled": 30,
                    },
                    "top_origins": [
                        {
                            "address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                            "pct_value": 20,
                            "entity_class": "exchange_vasp",
                            "label": "Binance",
                        },
                        {
                            "address": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                            "pct_value": 12,
                            "entity_class": "exchange_deposit_inferred",
                            "label": "inferred→Binance",
                        },
                    ],
                    "total_weight": 1000,
                },
                "nested": {"x": 1},
            },
            "hops": [
                {
                    "address": "0x1111111111111111111111111111111111111111",
                    "hop": 1,
                    "weight": 25,
                    "grade": "A",
                    "summary": None,
                    "is_normal_wallet": True,
                    "signals": {
                        "sanctions_hit": False,
                        "mixer_hit": False,
                        "mixing_risk": False,
                        "cex_hit": False,
                        "cex_name": None,
                        "bridge_hit": False,
                        "primary_category": "organic",
                        "entity_class": "unlabeled",
                        "chain_id": 137,
                        "ankr_slug": "matic-mainnet",
                        "weight_to_subject": 25,
                        "fetched_txs": 10,
                    },
                },
                {
                    "address": "0x3333333333333333333333333333333333333333",
                    "hop": 1,
                    "weight": 75,
                    "grade": "D",
                    "summary": None,
                    "is_normal_wallet": False,
                    "signals": {
                        "sanctions_hit": False,
                        "mixer_hit": False,
                        "mixing_risk": False,
                        "cex_hit": False,
                        "cex_name": None,
                        "bridge_hit": True,
                        "primary_category": "bridge",
                        "entity_class": "bridge",
                        "chain_id": 137,
                        "ankr_slug": "matic-mainnet",
                        "weight_to_subject": 75,
                        "fetched_txs": 40,
                    },
                },
                {
                    "address": "0x4444444444444444444444444444444444444444",
                    "hop": 2,
                    "via": "0x1111111111111111111111111111111111111111",
                    "weight": 40,
                    "grade": "A",
                    "summary": None,
                    "is_normal_wallet": True,
                    "signals": {
                        "sanctions_hit": False,
                        "mixer_hit": False,
                        "mixing_risk": False,
                        "cex_hit": False,
                        "cex_name": None,
                        "bridge_hit": False,
                        "primary_category": "organic",
                        "entity_class": "unlabeled",
                        "chain_id": 137,
                        "ankr_slug": "matic-mainnet",
                        "weight_to_subject": 40,
                        "fetched_txs": 20,
                    },
                },
                {
                    "address": "0x5555555555555555555555555555555555555555",
                    "hop": 2,
                    "via": "0x3333333333333333333333333333333333333333",
                    "weight": 60,
                    "grade": "C",
                    "summary": None,
                    "is_normal_wallet": False,
                    "signals": {
                        "sanctions_hit": False,
                        "mixer_hit": False,
                        "mixing_risk": False,
                        "cex_hit": True,
                        "cex_name": "OKX",
                        "bridge_hit": False,
                        "primary_category": "cex",
                        "entity_class": "exchange",
                        "chain_id": 137,
                        "ankr_slug": "matic-mainnet",
                        "weight_to_subject": 60,
                        "fetched_txs": 15,
                    },
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
                "kleros_tagged_contract_pct": 0.22,
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
                    "in_weight": 80.0,
                    "out_weight": 19.1,
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
            "signals": {
                "main_chains": [
                    {
                        "name": "Base",
                        "chain_id": 8453,
                        "last_tx_at": "2026-09-03T04:42:39Z",
                    },
                    {
                        "name": "OP Mainnet",
                        "chain_id": 10,
                        "last_tx_at": "2026-09-03T02:06:03Z",
                    },
                ]
            },
        },
        "portfolio": {
            "grade": "B",
            "summary": {"esp": "Portafolio calificado B (Bueno).", "eng": "Portfolio graded B."},
            "highlights": {
                "credible_value_usd": 15.17,
                "liquid_ratio": 1,
                "dust_ratio": 0.073,
            },
            "signals": {
                "native_gas_buffer_usd": 11.79,
                "native_gas_buffer_positions": 1,
                "total_value_usd_credible": 14.12,
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
    assert ctx["custody"] is not None
    assert ctx["custody"]["title"] == "Clasificación de custodia"
    custody_labels = {r["label"] for r in ctx["custody"]["rows"]}
    assert "Clase" in custody_labels
    assert "Prob. hosted" in custody_labels
    assert "Probablemente unhosted" in {r["value"] for r in ctx["custody"]["rows"]}
    assert ctx["mod_origins"]["clusters"] is not None
    assert ctx["mod_origins"]["clusters"]["title"] == "Origen por clase de entidad"
    assert ctx["analisis_url"] == "https://gateway.pinata.cloud/ipfs/QmAnalisis"
    assert ctx["evidencia_url"] == "https://gateway.pinata.cloud/ipfs/QmEvidencia"
    assert ctx["synthesis_label"] == "Bueno"
    assert "Lectura global B" in ctx["synthesis_summary"]
    assert len(ctx["overview_modules"]) == 4
    assert ctx["id_label"] == "Identificación:"
    assert ctx["footer_created_by"] == "Análisis creado y distribuido por Walpulse"
    assert "footer_note" not in ctx
    assert len(ctx["data_providers"]) == 7
    assert ctx["data_providers"][0]["links"][0]["name"] == "Goldrush"
    assert "presencia on-chain" in ctx["data_providers"][0]["role"]


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
    assert "Kleros-tagged contracts" in signal_labels
    assert "Sourcify verified" in signal_labels
    origins_labels = {r["label"] for r in ctx["mod_origins"]["signals"]}
    assert "Inferred CEX deposit (% value)" in origins_labels
    assert "Spellbook-labeled CEX (% value)" in origins_labels
    assert ctx["custody"]["title"] == "Custody classification"
    assert ctx["mod_origins"]["clusters"]["title"] == "Origin by entity class"
    assert ctx["footer_created_by"] == "Analysis created and distributed by Walpulse"
    assert "must not be decisive" in ctx["footer_signals_disclaimer"]
    assert "Query on-chain presence" in ctx["data_providers"][0]["role"]
    assert "and other public providers" in ctx["data_providers"][-1]["extra_label"]


def test_build_template_context_pt_footer_providers():
    ctx = build_template_context(
        request_id="11111111-1111-1111-1111-111111111111",
        tier="estandar",
        wallet="0xabc",
        analisis=FIXTURE,
        data_hash=None,
        analisis_cid=None,
        evidencia_cid=None,
        logo_uri=None,
        idioma="pt",
    )
    assert ctx["html_lang"] == "pt"
    assert ctx["id_label"] == "Identificação:"
    assert "distribuída por Walpulse" in ctx["footer_created_by"]
    assert "presença on-chain" in ctx["data_providers"][0]["role"]
    assert "outros provedores públicos" in ctx["data_providers"][-1]["extra_label"]


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
    assert "Contratos etiquetados Kleros" in labels
    assert "Sourcify verificado" in labels
    assert "Puntaje wash" in labels
    assert len(activity["signals"]) >= 16
    assert values_by_label["Sourcify verificado"] == "25%"
    assert values_by_label["Contratos etiquetados Kleros"] == "22%"
    assert "_" not in "".join(labels)


def test_signals_override_stale_highlights_for_kleros():
    """PDF must show aggregated signals, not biased/stale highlights (e.g. per-chain 0%)."""
    analisis = copy.deepcopy(FIXTURE)
    analisis["modules"]["activity"]["highlights"] = {
        "kleros_tagged_counterparty_pct": 0,
        "kleros_tagged_contract_pct": 0,
        "sourcify_verified_pct": 0,
        "unique_counterparties": 19,
        "sanctions_hit": False,
    }
    analisis["modules"]["activity"]["signals"] = {
        **analisis["modules"]["activity"]["signals"],
        "kleros_tagged_counterparty_pct": 0.5043028629068855,
        "kleros_tagged_contract_pct": 0.4140713356789518,
        "sourcify_verified_pct": 0.44952950043016526,
        "unique_counterparties": 54,
    }
    ctx = build_template_context(
        request_id="368593d0-60ca-4668-bb73-82b5d47a8076",
        tier="estandar",
        wallet="0x9e51bbd7584afd0fb2e4bddab37f23a9f192d30a",
        analisis=analisis,
        data_hash=None,
        analisis_cid=None,
        evidencia_cid=None,
        logo_uri=None,
        idioma="en",
    )
    values = {r["label"]: r["value"] for r in ctx["mod_activity"]["signals"]}
    assert values["Kleros-tagged counterparties"] == "50.43%"
    assert values["Kleros-tagged contracts"] == "41.41%"
    assert values["Sourcify verified"] == "44.95%"
    assert values["Unique counterparties"] == "54"


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
    assert origins["hops_title"] == "Hops / screening de fondeadores"
    assert "no es un re-análisis Origins" in origins["hops_blurb"]
    assert "Contexto de quién fondeó" in origins["hops_blurb"]
    # Ordered by hop1 weight desc: 75% first (1a), then 25% (1b)
    assert len(origins["hop_groups"]) == 2
    branch_a = origins["hop_groups"][0]
    branch_b = origins["hop_groups"][1]
    assert branch_a["cards"][0]["tag"] == "Hop 1a"
    assert branch_a["cards"][0]["address"].startswith("0x3333")
    assert branch_a["cards"][0]["weight"] == "75%"
    assert branch_a["cards"][0]["grade"] == "D"
    assert branch_a["cards"][0]["funder_risk"] is True
    assert any(f["key"] == "bridge" and f["hit"] for f in branch_a["cards"][0]["flags"])
    assert any(f["label"] == "Bridge: Sí" for f in branch_a["cards"][0]["flags"])
    assert any(f["label"] == "OFAC: No" for f in branch_a["cards"][0]["flags"])
    assert "Screening de fondeador" in branch_a["cards"][0]["summary"]
    assert "Bridge" in branch_a["cards"][0]["summary"]
    assert "re-análisis Origins" not in branch_a["cards"][0]["summary"]
    assert "Contexto de quién fondeó" not in branch_a["cards"][0]["summary"]
    assert branch_a["cards"][1]["tag"] == "Hop 2a"
    assert branch_a["cards"][1]["via"] == "0x3333333333333333333333333333333333333333"
    assert branch_a["cards"][1]["weight"] == "100%"
    assert "CEX: Sí (OKX)" in [f["label"] for f in branch_a["cards"][1]["flags"]]
    assert "CEX (OKX)" in branch_a["cards"][1]["summary"]
    assert branch_b["cards"][0]["tag"] == "Hop 1b"
    assert branch_b["cards"][0]["weight"] == "25%"
    assert branch_b["cards"][0]["grade"] == "A"
    assert "sin señales OFAC" in branch_b["cards"][0]["summary"]
    assert all(f["label"].endswith(": No") for f in branch_b["cards"][0]["flags"])
    assert branch_b["cards"][1]["tag"] == "Hop 2b"
    assert branch_b["cards"][1]["via"] == "0x1111111111111111111111111111111111111111"
    assert ctx["via_label"] == "Wallet fondeada"
    assert ctx["hop_flags_legend"] == "Señales del fondeador (sí/no)"
    assert activity["hops_title"] == "Contrapartes top analizadas"
    assert activity["hop_groups"][0]["cards"][0]["grade"] == "D"
    assert activity["hop_groups"][0]["cards"][0]["weight"] == "100%"
    assert activity["hop_groups"][0]["cards"][0]["flow_in"] == "80.7%"
    assert activity["hop_groups"][0]["cards"][0]["flow_out"] == "19.3%"
    assert "Contraparte top débil" in activity["hop_groups"][0]["cards"][0]["summary"]
    assert activity["hop_groups"][0]["cards"][0]["flags"] == []
    assert activity.get("hops_blurb", "") == ""
    assert ctx["hop_meta_in"] == "Entrada"
    assert ctx["hop_meta_out"] == "Salida"


def test_activity_top_counterparties_fallback_estandar():
    analisis = copy.deepcopy(FIXTURE)
    analisis["modules"]["activity"]["counterparties_light"] = []
    analisis["modules"]["activity"]["top_counterparties"] = [
        {
            "address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "weight": 100,
            "in_weight": 60,
            "out_weight": 40,
        },
        {
            "address": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "weight": 50,
            "in_weight": 50,
            "out_weight": 0,
        },
    ]
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
    activity = ctx["mod_activity"]
    assert activity["hops_title"] == "Contrapartes top"
    cards = activity["hop_groups"][0]["cards"]
    assert len(cards) == 2
    assert cards[0]["weight"] == "66.7%"
    assert cards[0]["flow_in"] == "60%"
    assert cards[0]["flow_out"] == "40%"
    assert cards[1]["weight"] == "33.3%"
    assert cards[1]["flow_in"] == "100%"
    assert cards[1]["flow_out"] == "0%"
    html = render_html(ctx)
    assert "Entrada: 60%" in html
    assert "Salida: 40%" in html


def test_activity_legacy_without_in_out_omits_flow():
    analisis = copy.deepcopy(FIXTURE)
    analisis["modules"]["activity"]["counterparties_light"] = [
        {
            "address": "0xcccccccccccccccccccccccccccccccccccccccc",
            "weight": 10,
            "tier": "basica",
            "grade": "C",
            "summary": {"esp": "Legacy sin in/out.", "eng": "Legacy no in/out."},
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
    card = ctx["mod_activity"]["hop_groups"][0]["cards"][0]
    assert card["weight"] == "100%"
    assert card["flow_in"] == ""
    assert card["flow_out"] == ""
    html = render_html(ctx)
    assert "Entrada:" not in html


def test_funder_risk_hop_error_summary():
    analisis = copy.deepcopy(FIXTURE)
    analisis["modules"]["origins"]["hops"] = [
        {
            "address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "hop": 1,
            "weight": 1,
            "error": "missing_dominant_chain",
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
    hop = ctx["mod_origins"]["hop_groups"][0]["cards"][0]
    assert hop["grade"] == "—"
    assert "Screening no disponible" in hop["summary"]
    assert "missing_dominant_chain" in hop["summary"]
    assert hop["flags"] == []

def test_excluded_hop_and_light_show_reason():
    analisis = copy.deepcopy(FIXTURE)
    analisis["modules"]["origins"]["hops"] = [
        {
            "address": "0xe7804c37c13166ff0b37f5ae0bb07a3aebb6e245",
            "hop": 1,
            "weight": 1,
            "skipped": True,
            "skip_reason": "cex_label",
            "cex_name": "Binance",
            "grade": None,
            "signals": None,
            "summary": None,
        }
    ]
    analisis["modules"]["activity"]["counterparties_light"] = [
        {
            "address": "0x" + "ce" * 20,
            "weight": 1,
            "tier": "basica",
            "skipped": True,
            "skip_reason": "cex_catalog",
            "cex_name": "Kraken",
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
    hop = ctx["mod_origins"]["hop_groups"][0]["cards"][0]
    light = ctx["mod_activity"]["hop_groups"][0]["cards"][0]
    assert hop["grade"] == "—"
    assert "excluida" in hop["summary"].lower()
    assert "etiqueta CEX" in hop["summary"]
    assert "cex_label" not in hop["summary"]
    assert "Binance" in hop["summary"]
    assert [f["label"] for f in hop["flags"]] == [
        "OFAC: No",
        "Mixer: No",
        "CEX: Sí (Binance)",
        "Bridge: No",
    ]
    assert hop["flags"][2]["hit"] is True
    assert "excluida" in light["summary"].lower()
    assert "catálogo CEX" in light["summary"]
    assert "cex_catalog" not in light["summary"]
    assert "Kraken" in light["summary"]
    assert light["flags"] == []


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
            "via": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
    branch = ctx["mod_origins"]["hop_groups"][0]
    assert branch["cards"][0]["tag"] == "Hop 1a"
    assert branch["cards"][0]["grade"] == "D"
    assert "Hop legacy D" in branch["cards"][0]["summary"]
    assert branch["cards"][0]["weight"] == "100%"
    assert branch["cards"][1]["tag"] == "Hop 2a"
    assert branch["cards"][1]["grade"] == "C"
    assert branch["cards"][1]["weight"] == "100%"
    assert branch["cards"][1]["via"]
    assert ctx["mod_activity"]["hop_groups"][0]["cards"][0]["grade"] == "F"
    assert "Light legacy F" in ctx["mod_activity"]["hop_groups"][0]["cards"][0]["summary"]
    assert ctx["mod_activity"]["hop_groups"][0]["cards"][0]["weight"] == "100%"


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
    assert "Clasificación de custodia" in page1
    assert "Probablemente unhosted" in page1
    assert "Compliance screen OFAC" not in page1
    assert page1.index("Vista general") < page1.index("Clasificación de custodia")
    assert page1.index("Clasificación de custodia") < page1.index(
        'class="module-name display">Multichain</h3>'
    )
    assert 'class="module-name display">Multichain</h3>' in page1
    assert "Chains con actividad" in page1
    assert "Base" in page1
    assert "OP Mainnet" in page1
    assert 'class="disclaimer"' not in page1
    assert "ipfs-help" not in page1
    assert 'class="module-name display">Portafolio</h3>' in page2
    assert "Compliance screen OFAC" in page2
    assert page2.index("Portafolio") < page2.index("Compliance screen OFAC")
    assert "Origen por clase de entidad" in page3
    assert "Exchange / VASP etiquetado" in page3
    assert "Depósito CEX inferido" in page3
    assert "Hops / screening de fondeadores" in page3
    assert "Screening de riesgo de los principales fondeadores" in page3
    assert "Hop 1a" in page3
    assert "Screening de fondeador" in page3
    assert "hop-flag" in page3
    assert "Hop 2a" in page3
    assert page3.index("Origen por clase de entidad") < page3.index("Hops / screening de fondeadores")
    assert "Actividad" in page4
    assert "Contratos etiquetados Kleros" in page4
    assert "Contrapartes top" in page4
    assert "Entrada:" in page4
    assert "Salida:" in page4
    assert "Data Providers" in page4
    assert "Goldrush" in page4
    assert "Zerion" in page4
    assert "Nsgood" in page4
    assert page4.index("Actividad") < page4.index("Data Providers")
    assert page4.index("Data Providers") < page4.index('class="disclaimer"')
    assert 'class="disclaimer"' in page4
    assert "ipfs-help" in page4
    assert 'class="running-footer"' in html
    assert "Identificación:" in html
    assert "Análisis creado y distribuido por Walpulse" in html
    assert "no debe ser decisorio" in html
    assert "0xdead" not in page4
    assert "Vista derivada" not in page4
    assert "Derived view" not in page4
    assert 'class="footer mono"' not in html
    assert 'class="footer-row"' not in html
    # request_id appears in running footer (document-level), not as labeled body footer
    assert html.count("11111111-1111-1111-1111-111111111111") >= 1


def test_custody_and_clusters_context():
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
    custody = ctx["custody"]
    assert custody["available"] is True
    by_label = {r["label"]: r["value"] for r in custody["rows"]}
    assert by_label["Prob. hosted"] == "18%"
    assert by_label["Prob. unhosted"] == "62%"
    assert by_label["Prob. desconocida"] == "20%"
    assert by_label["Confianza"] == "Media"
    assert len(custody["evidence"]) == 2
    assert "no prueba control de claves" in custody["disclaimer"]

    clusters = ctx["mod_origins"]["clusters"]
    assert clusters is not None
    cluster_by = {r["label"]: r["value"] for r in clusters["rows"]}
    assert cluster_by["Exchange / VASP etiquetado"] == "35%"
    assert cluster_by["Depósito CEX inferido"] == "12%"
    assert "Mixer" not in cluster_by  # zero omitted
    assert len(clusters["top_origins"]) == 2
    assert clusters["top_origins"][0]["label"] == "Binance"

    origins_by = {r["label"]: r["value"] for r in ctx["mod_origins"]["signals"]}
    assert origins_by["Depósito CEX inferido (% valor)"] == "12%"
    assert origins_by["CEX etiquetado Spellbook (% valor)"] == "35%"


def test_custody_missing_omitted():
    analisis = copy.deepcopy(FIXTURE)
    del analisis["custody_classification"]
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
    assert ctx["custody"] is None
    html = render_html(ctx)
    assert "Clasificación de custodia" not in html


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
    assert by_label["Valor credible (USD)"] == "$15.17"
    assert by_label["Buffer de gas nativo (USD)"] == "$11.79"
    assert by_label["Posiciones buffer de gas"] == "1"
    assert by_label["Valor total credible (USD)"] == "$14.12"
    activity_by = {r["label"]: r["value"] for r in ctx["mod_activity"]["signals"]}
    assert activity_by["HHI de contrapartes"] == "50%"
    origins_by = {r["label"]: r["value"] for r in ctx["mod_origins"]["signals"]}
    assert origins_by["HHI USD"] == "42%"


def test_multichain_chains_section():
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
    chains = ctx["mod_multichain"]["chains"]
    assert ctx["mod_multichain"]["chains_title"] == "Chains con actividad"
    assert chains[0]["name"] == "Base"
    assert chains[0]["last_tx"].startswith("2026-09-03")
    assert chains[1]["name"] == "OP Mainnet"


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
    assert "Hops / screening de fondeadores" in html
    assert "Contrapartes top analizadas" in html
    assert "Contrapartes etiquetadas Kleros" in html
    assert "Contratos etiquetados Kleros" in html
    assert "Clasificación de custodia" in html
    assert "Origen por clase de entidad" in html
    assert "kleros_tagged" not in html
    assert "origin_entity_clusters" not in html
    assert "custody_classification" not in html
    for match in re.findall(r'class="signal-label">([^<]+)<', html):
        assert "_" not in match


def test_signal_catalog_covers_fixture_keys():
    activity = FIXTURE["modules"]["activity"]
    keys = set(activity["highlights"]) | set(activity["signals"])
    keys -= {"nested"}
    missing = [k for k in keys if k not in SIGNAL_LABELS]
    assert missing == []

    origins = FIXTURE["modules"]["origins"]
    origin_keys = set(origins["highlights"]) | set(origins["signals"])
    origin_keys -= {"nested", "origin_entity_clusters"}
    missing_origins = [k for k in origin_keys if k not in SIGNAL_LABELS]
    assert missing_origins == []


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
