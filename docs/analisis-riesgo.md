# Analisis Riesgo — worker

Evalúa el **Motor de Riesgos** del cliente sobre el envelope `analisis-v1` en **Storage** (`analisis-artifacts`).

**Orden:** `analisis_run` → `analisis_riesgo` (si hay matrices) → `analisis_pdf` → `analisis_email`

## Cola

`list_analisis_requests_pending_riesgo`:

- tier `estandar` \| `experta`
- status `succeeded` \| `succeeded_with_warnings`
- `has_analisis_artifact` (o jsonb residual legacy)
- `riesgo_evaluado_at IS NULL`

## Storage-only

1. `require_artifact(..., "analisis")` — sin fallback jsonb
2. Evaluar matrices
3. `put` kind `riesgo` → `set_analisis_request_riesgo` (solo control: `riesgo_evaluado_at` + `tiene_evaluaciones_riesgo`; **no** persiste columna `riesgo`)

## Skip sin matrices

Si el cliente no tiene sandbox ni matrices en producción, **`analisis_run`** (o este worker) llama `set_analisis_request_riesgo` con:

```json
{ "schema": "riesgo-evaluacion-v1", "skipped_reason": "sin_matrices_activas", "evaluations": [] }
```

(tras upload Storage). Así el PDF no espera otro poll.

## Evaluación

1. `get_cliente_riesgo_matrices_activas(cliente_id)` → sandbox (0..1) + prod (N)
2. Por cada regla habilitada: leer `senales.json_path` del `analisis`, aplicar `operador`/`umbral`
3. Agregación `per_chain` / `hop`: **matchea si alguna** instancia cumple
4. Puntaje = suma de `efecto.valor` de reglas matched
5. Upload Storage + `set_analisis_request_riesgo(id, envelope)` (flags)

## Envelope

Ver [analisis-riesgo.md](https://github.com/walpulse/database/blob/main/docs/analisis-riesgo.md) en `walpulse/database`.

## GHA

`.github/workflows/analisis-riesgo.yml` — cron `1 */6 * * *`, poll 45 s, secrets `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`.

## Downstream

`analisis_pdf` lee `riesgo` y, si hay `evaluations`, genera el PDF Motor (`riesgo_cid`). Skip `sin_matrices_activas` no produce ese PDF.
