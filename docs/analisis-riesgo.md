# Analisis Riesgo — worker

Evalúa el **Motor de Riesgos** del cliente sobre el envelope `analisis-v1` ya persistido.

**Orden:** `analisis_run` → `analisis_riesgo` (si hay matrices) → `analisis_pdf` → `analisis_email`

## Cola

`list_analisis_requests_pending_riesgo`:

- tier `estandar` \| `experta`
- status `succeeded` \| `succeeded_with_warnings`
- `analisis` not null
- `riesgo_evaluado_at IS NULL`

## Skip sin matrices

Si el cliente no tiene sandbox ni matrices en producción, **`analisis_run`** llama `set_analisis_request_riesgo` con:

```json
{ "schema": "riesgo-evaluacion-v1", "skipped_reason": "sin_matrices_activas", "evaluations": [] }
```

Así el PDF no espera otro poll. Este worker es red de seguridad si quedara alguna fila pendiente sin matrices.

## Evaluación

1. `get_cliente_riesgo_matrices_activas(cliente_id)` → sandbox (0..1) + prod (N)
2. Por cada regla habilitada: leer `senales.json_path` del `analisis`, aplicar `operador`/`umbral`
3. Agregación `per_chain` / `hop`: **matchea si alguna** instancia cumple
4. Puntaje = suma de `efecto.valor` de reglas matched
5. `set_analisis_request_riesgo(id, envelope)`

## Envelope

Ver [analisis-riesgo.md](https://github.com/walpulse/database/blob/main/docs/analisis-riesgo.md) en `walpulse/database`.

## GHA

`.github/workflows/analisis-riesgo.yml` — cron `1 */6 * * *`, poll 45 s, secrets `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`.

## Downstream

`analisis_pdf` lee `riesgo` y, si hay `evaluations`, genera el PDF Motor (`riesgo_cid`). Skip `sin_matrices_activas` no produce ese PDF.
