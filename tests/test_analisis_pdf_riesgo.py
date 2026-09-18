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
                    "umbral": {"value": True},
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
                    "umbral": {"value": 0.5},
                    "valor_observado": 0.1,
                    "matched": False,
                    "puntos": 0,
                },
                {
                    "regla_id": "r2b",
                    "codigo": "age_lt",
                    "nombre": "Edad corta",
                    "operador": "lt",
                    "umbral": {"value": 15},
                    "valor_observado": 3,
                    "matched": True,
                    "puntos": 5,
                },
                {
                    "regla_id": "r2c",
                    "codigo": "flag_true",
                    "nombre": "Flag verdadero",
                    "operador": "is_true",
                    "umbral": {},
                    "valor_observado": True,
                    "matched": True,
                    "puntos": 2,
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
                    "operador": "between",
                    "umbral": {"min": 80, "max": 100},
                    "valor_observado": 12,
                    "matched": False,
                    "puntos": 0,
                },
            ],
        },
    ],
}

ENRICHMENT_FIXTURE = {
    "cliente_nombre": "Cliente Demo",
    "versions": [
        {"version_id": "v-s", "version_num": 2, "nombre": "Borrador sandbox", "notas": None},
        {"version_id": "v-p", "version_num": 1, "nombre": None, "notas": "Notas prod"},
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
        enrichment=ENRICHMENT_FIXTURE,
    )
    assert ctx["doc_title"] == "Motor de Riesgos"
    assert ctx["tier_label"] == "Estándar"
    assert ctx["matched_title"] == "Reglas aplicadas"
    assert ctx["unmatched_title"] == "Reglas sin aplicar"
    assert len(ctx["evaluations"]) == 2
    first = ctx["evaluations"][0]
    assert first["ambiente_label"] == "Sandbox"
    assert first["score_display"] == "15 / 40"
    assert first["cliente_nombre"] == "Cliente Demo"
    assert first["version_nombre"] == "Borrador sandbox"
    assert first["version_notas"] == "—"
    labels = [r["label"] for r in first["identity_rows"]]
    assert "Cliente" in labels
    assert "Nombre de la matriz" in labels
    assert len(first["matched_rows"]) == 3
    assert first["matched_rows"][0]["condition"] == "Igual a true"
    assert first["matched_rows"][1]["condition"] == "Menor que 15"
    assert first["matched_rows"][2]["condition"] == "Es verdadero"
    assert first["unmatched_rows"][0]["condition"] == "Mayor o igual que 0.5"
    assert ctx["evaluations"][1]["ambiente_label"] == "Producción"
    assert ctx["evaluations"][1]["version_nombre"] == "—"
    assert ctx["evaluations"][1]["version_notas"] == "Notas prod"
    assert ctx["evaluations"][1]["unmatched_rows"][0]["condition"] == "Entre 80 – 100"


def test_build_riesgo_context_en():
    ctx = build_riesgo_template_context(
        request_id="11111111-1111-1111-1111-111111111111",
        tier="experta",
        wallet="0xabc",
        riesgo=RIESGO_FIXTURE,
        idioma="en",
        enrichment=ENRICHMENT_FIXTURE,
    )
    assert ctx["doc_title"] == "Risk Engine"
    assert ctx["tier_label"] == "Expert"
    assert ctx["evaluations"][1]["ambiente_label"] == "Production"
    assert ctx["matched_title"] == "Applied rules"
    assert ctx["unmatched_title"] == "Not applied rules"
    assert ctx["evaluations"][0]["matched_rows"][1]["condition"] == "Less than 15"
    assert ctx["evaluations"][0]["matched_rows"][2]["condition"] == "Is true"


def test_render_riesgo_html_contains_matrix_names():
    ctx = build_riesgo_template_context(
        request_id="11111111-1111-1111-1111-111111111111",
        tier="estandar",
        wallet="0xabc",
        riesgo=RIESGO_FIXTURE,
        idioma="es",
        enrichment=ENRICHMENT_FIXTURE,
    )
    html = render_riesgo_html(ctx)
    assert "Matriz sandbox demo" in html
    assert "PSAV default" in html
    assert "Exposición OFAC" in html
    assert "Motor de Riesgos" in html
    assert "Cliente Demo" in html
    assert "Reglas aplicadas" in html
    assert "Reglas sin aplicar" in html
    assert "Menor que 15" in html
    assert "Es verdadero" in html
    assert "page-break" not in html
    assert ">Código<" not in html
    assert "ofac_hit" not in html


def test_render_riesgo_pdf_bytes_smoke():
    try:
        pdf = render_riesgo_pdf_bytes(
            request_id="11111111-1111-1111-1111-111111111111",
            tier="estandar",
            wallet="0xabc",
            riesgo=RIESGO_FIXTURE,
            idioma="es",
            enrichment=ENRICHMENT_FIXTURE,
        )
    except (ImportError, OSError):
        pytest.skip("WeasyPrint not available")
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1000
