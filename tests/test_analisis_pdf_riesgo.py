"""Tests for analisis_pdf Motor de Riesgos render."""

from __future__ import annotations

import pytest

from workers.analisis_pdf.render_riesgo import (
    build_riesgo_template_context,
    has_riesgo_evaluations,
    render_riesgo_html,
    render_riesgo_pdf_bytes,
)

RIESGO_FIXTURE = {
    "schema": "riesgo-evaluacion-v1",
    "skipped_reason": None,
    "evaluated_at": "2026-09-18T03:00:00+00:00",
    "analisis_request_id": "11111111-1111-1111-1111-111111111111",
    "evaluations": [
        {
            "ambiente": "sandbox",
            "matriz_id": "m-sandbox",
            "matriz_slug": "demo-sandbox",
            "matriz_nombre": "Matriz sandbox demo",
            "version_id": "v-s",
            "version_num": 2,
            "puntaje": 15,
            "presupuesto_puntos": 40,
            "reglas": [
                {
                    "regla_id": "r1",
                    "codigo": "ofac_hit",
                    "nombre": "Exposición OFAC",
                    "senal_codigo": "sanctions_hit",
                    "operador": "eq",
                    "umbral": {"valor": True},
                    "valor_observado": True,
                    "matched": True,
                    "puntos": 15,
                },
                {
                    "regla_id": "r2",
                    "codigo": "mixer_low",
                    "nombre": "Mixing bajo",
                    "senal_codigo": "mixing_risk",
                    "operador": "gte",
                    "umbral": {"valor": 0.5},
                    "valor_observado": 0.1,
                    "matched": False,
                    "puntos": 0,
                },
            ],
        },
        {
            "ambiente": "produccion",
            "matriz_id": "m-prod",
            "matriz_slug": "psav-default",
            "matriz_nombre": "PSAV default",
            "version_id": "v-p",
            "version_num": 1,
            "puntaje": 0,
            "presupuesto_puntos": 25,
            "reglas": [
                {
                    "regla_id": "r3",
                    "codigo": "cex_high",
                    "nombre": "Alta concentración CEX",
                    "operador": "gte",
                    "umbral": {"min": 80},
                    "valor_observado": 12,
                    "matched": False,
                    "puntos": 0,
                },
            ],
        },
    ],
}

SKIP_FIXTURE = {
    "schema": "riesgo-evaluacion-v1",
    "skipped_reason": "sin_matrices_activas",
    "evaluations": [],
    "evaluated_at": "2026-09-18T03:00:00+00:00",
}


def test_has_riesgo_evaluations():
    assert has_riesgo_evaluations(RIESGO_FIXTURE) is True
    assert has_riesgo_evaluations(SKIP_FIXTURE) is False
    assert has_riesgo_evaluations({"evaluations": []}) is False
    assert has_riesgo_evaluations(None) is False


def test_build_riesgo_context_es():
    ctx = build_riesgo_template_context(
        request_id="11111111-1111-1111-1111-111111111111",
        tier="estandar",
        wallet="0xabc",
        riesgo=RIESGO_FIXTURE,
        idioma="es",
    )
    assert ctx["doc_title"] == "Motor de Riesgos"
    assert ctx["tier_label"] == "Estándar"
    assert len(ctx["summary_cards"]) == 2
    assert ctx["summary_cards"][0]["ambiente_label"] == "Sandbox"
    assert ctx["summary_cards"][0]["score_display"] == "15 / 40"
    assert ctx["summary_cards"][1]["ambiente_label"] == "Producción"
    assert len(ctx["evaluations"][0]["matched_rows"]) == 1
    assert len(ctx["evaluations"][0]["unmatched_rows"]) == 1
    assert "eq" in ctx["evaluations"][0]["matched_rows"][0]["condition"]


def test_build_riesgo_context_en():
    ctx = build_riesgo_template_context(
        request_id="11111111-1111-1111-1111-111111111111",
        tier="experta",
        wallet="0xabc",
        riesgo=RIESGO_FIXTURE,
        idioma="en",
    )
    assert ctx["doc_title"] == "Risk Engine"
    assert ctx["tier_label"] == "Expert"
    assert ctx["summary_cards"][1]["ambiente_label"] == "Production"
    assert ctx["matched_title"] == "Triggered rules"


def test_render_riesgo_html_contains_matrix_names():
    ctx = build_riesgo_template_context(
        request_id="11111111-1111-1111-1111-111111111111",
        tier="estandar",
        wallet="0xabc",
        riesgo=RIESGO_FIXTURE,
        idioma="es",
    )
    html = render_riesgo_html(ctx)
    assert "Matriz sandbox demo" in html
    assert "PSAV default" in html
    assert "Exposición OFAC" in html
    assert "Motor de Riesgos" in html


def test_render_riesgo_pdf_bytes_smoke():
    try:
        pdf = render_riesgo_pdf_bytes(
            request_id="11111111-1111-1111-1111-111111111111",
            tier="estandar",
            wallet="0xabc",
            riesgo=RIESGO_FIXTURE,
            idioma="es",
        )
    except ImportError:
        pytest.skip("WeasyPrint not available")
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1000
