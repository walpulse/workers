"""Unit tests for Motor de Riesgos evaluator."""

from __future__ import annotations

from workers.analisis_riesgo.evaluate import evaluate_request, skip_envelope
from workers.analisis_riesgo.extract import collect_values
from workers.analisis_riesgo.ops import matches


def test_ops_comparisons() -> None:
    assert matches("gt", 0.7, {"value": 0.5})
    assert not matches("gt", 0.4, {"value": 0.5})
    assert matches("between", 5, {"min": 1, "max": 10})
    assert matches("in", "hosted_known", {"values": ["hosted_known", "unknown"]})
    assert matches("is_true", True, {})
    assert matches("is_null", None, {})
    assert matches("not_null", 1, {})


def test_extract_aggregate_and_per_chain() -> None:
    analisis = {
        "modules": {
            "origins": {
                "signals": {"hhi": 0.42},
                "per_chain": [
                    {"concentration": {"top3_share": 0.8}},
                    {"concentration": {"top3_share": 0.2}},
                ],
            }
        }
    }
    assert collect_values(analisis, "modules.origins.signals.hhi", "aggregate") == [0.42]
    vals = collect_values(
        analisis,
        "modules.origins.per_chain[].concentration.top3_share",
        "per_chain",
    )
    assert vals == [0.8, 0.2]


def test_evaluate_matriz_puntaje() -> None:
    analisis = {
        "modules": {"origins": {"signals": {"hhi": 0.9}}},
        "custody_classification": {"class": "likely_unhosted"},
    }
    matrices = [
        {
            "ambiente": "produccion",
            "matriz_id": "m1",
            "matriz_slug": "default",
            "matriz_nombre": "Default",
            "version_id": "v1",
            "version_num": 1,
            "reglas": [
                {
                    "regla_id": "r1",
                    "codigo": "origins.hhi.gt",
                    "nombre": "HHI alto",
                    "habilitada": True,
                    "operador": "gt",
                    "umbral": {"value": 0.5},
                    "efecto": {"tipo": "puntos", "valor": 40},
                    "senal": {
                        "codigo": "origins.hhi",
                        "json_path": "modules.origins.signals.hhi",
                        "agregacion": "aggregate",
                    },
                },
                {
                    "regla_id": "r2",
                    "codigo": "custody.class.eq",
                    "nombre": "Unhosted",
                    "habilitada": True,
                    "operador": "eq",
                    "umbral": {"value": "likely_unhosted"},
                    "efecto": {"tipo": "puntos", "valor": 20},
                    "senal": {
                        "codigo": "custody.class",
                        "json_path": "custody_classification.class",
                        "agregacion": "root",
                    },
                },
            ],
        }
    ]
    out = evaluate_request(analisis, matrices, request_id="req-1")
    assert out["schema"] == "riesgo-evaluacion-v1"
    assert out["skipped_reason"] is None
    assert len(out["evaluations"]) == 1
    assert out["evaluations"][0]["puntaje"] == 60
    assert all(r["matched"] for r in out["evaluations"][0]["reglas"])


def test_per_chain_any_match() -> None:
    analisis = {
        "modules": {
            "origins": {
                "per_chain": [
                    {"direct_exposure": {"mixer": False}},
                    {"direct_exposure": {"mixer": True}},
                ]
            }
        }
    }
    matrices = [
        {
            "ambiente": "sandbox",
            "matriz_slug": "sbx",
            "version_id": "v",
            "version_num": 1,
            "reglas": [
                {
                    "codigo": "origins.pc.mixer.is_true",
                    "nombre": "Mixer",
                    "habilitada": True,
                    "operador": "is_true",
                    "umbral": {},
                    "efecto": {"tipo": "puntos", "valor": 50},
                    "senal": {
                        "codigo": "origins.pc.mixer",
                        "json_path": "modules.origins.per_chain[].direct_exposure.mixer",
                        "agregacion": "per_chain",
                    },
                }
            ],
        }
    ]
    out = evaluate_request(analisis, matrices)
    assert out["evaluations"][0]["puntaje"] == 50


def test_skip_without_matrices() -> None:
    out = evaluate_request({"modules": {}}, [])
    assert out["skipped_reason"] == "sin_matrices_activas"
    assert out["evaluations"] == []
    skip = skip_envelope("abc")
    assert skip["analisis_request_id"] == "abc"
