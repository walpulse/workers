"""Build riesgo-evaluacion-v1 envelope from analisis + active matrices."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from workers.analisis_riesgo.extract import collect_values, primary_value
from workers.analisis_riesgo.ops import matches

SCHEMA = "riesgo-evaluacion-v1"
SKIP_SIN_MATRICES = "sin_matrices_activas"


def skip_envelope(request_id: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "skipped_reason": SKIP_SIN_MATRICES,
        "evaluations": [],
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
    if request_id:
        out["analisis_request_id"] = str(request_id)
    return out


def _efecto_puntos(efecto: Any) -> int:
    if not isinstance(efecto, dict):
        return 0
    if (efecto.get("tipo") or "") != "puntos":
        return 0
    try:
        return max(0, int(efecto.get("valor") or 0))
    except (TypeError, ValueError):
        return 0


def evaluate_regla(analisis: dict[str, Any], regla: dict[str, Any]) -> dict[str, Any]:
    senal = regla.get("senal") if isinstance(regla.get("senal"), dict) else {}
    json_path = str(senal.get("json_path") or "")
    agregacion = str(senal.get("agregacion") or "aggregate")
    operador = str(regla.get("operador") or "")
    umbral = regla.get("umbral") if isinstance(regla.get("umbral"), dict) else {}
    efecto = regla.get("efecto") if isinstance(regla.get("efecto"), dict) else {}

    values = collect_values(analisis, json_path, agregacion)
    matched = any(matches(operador, v, umbral) for v in values)
    puntos = _efecto_puntos(efecto) if matched else 0
    observed = primary_value(values)

    return {
        "regla_id": regla.get("regla_id") or regla.get("id"),
        "codigo": regla.get("codigo"),
        "nombre": regla.get("nombre"),
        "senal_codigo": senal.get("codigo"),
        "json_path": json_path,
        "agregacion": agregacion,
        "valor_observado": observed,
        "operador": operador,
        "umbral": umbral,
        "matched": matched,
        "puntos": puntos,
        "efecto": efecto,
    }


def evaluate_matriz(
    analisis: dict[str, Any],
    matriz: dict[str, Any],
) -> dict[str, Any]:
    reglas_in = matriz.get("reglas") if isinstance(matriz.get("reglas"), list) else []
    reglas_out: list[dict[str, Any]] = []
    puntaje = 0
    presupuesto = 0
    for regla in reglas_in:
        if not isinstance(regla, dict):
            continue
        if regla.get("habilitada") is False:
            continue
        presupuesto += _efecto_puntos(regla.get("efecto"))
        row = evaluate_regla(analisis, regla)
        puntaje += int(row["puntos"])
        reglas_out.append(row)

    return {
        "ambiente": matriz.get("ambiente"),
        "matriz_id": matriz.get("matriz_id"),
        "matriz_slug": matriz.get("matriz_slug"),
        "matriz_nombre": matriz.get("matriz_nombre"),
        "version_id": matriz.get("version_id"),
        "version_num": matriz.get("version_num"),
        "puntaje": puntaje,
        "presupuesto_puntos": presupuesto,
        "reglas": reglas_out,
    }


def evaluate_request(
    analisis: dict[str, Any],
    matrices: list[dict[str, Any]],
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    if not matrices:
        return skip_envelope(request_id)

    evaluations = [
        evaluate_matriz(analisis, m)
        for m in matrices
        if isinstance(m, dict)
    ]
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "skipped_reason": None,
        "evaluations": evaluations,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
    if request_id:
        out["analisis_request_id"] = str(request_id)
    return out
