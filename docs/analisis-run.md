# analisis_run — orquestación Estándar / Experta

Worker GHA que **ejecuta** el pipeline async (claim FIFO + secuencia HTTP a Edges).  
No recalcula señales ni grades en Python.

| Campo | Valor |
|-------|--------|
| Código | `workers/analisis_run/` |
| Workflow | `.github/workflows/analisis-run.yml` |
| Claim | `claim_analisis_requests_for_run(≤5, 12)` |
| Paralelismo | `ThreadPoolExecutor(max_workers≤5)` — un client Supabase **por hilo** |
| Stages | RPCs `start/finish_analisis_run_stage` + `run_progress` |
| Poll | 45 s dentro de ventana ~6 h (`0 */6 * * *`) |
| Secrets | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` |

## Cadena

```
accept → accepted → analisis_run → analisis_pdf → analisis_email
```

## Paralelismo

Cada oneshot hace claim de hasta **5** filas y las procesa en paralelo dentro del mismo runner. El loop continuo espera a que termine el oneshot (backpressure). Concurrency GHA sigue `group: analisis-run` (un workflow a la vez). Un oneshot puede ocupar hasta ~90 min × cola mientras el step espera a los workers.

## Stages (telemetría)

`stages.py` instrumenta el pipeline: `ola1` → … → `custody` → `persist` → `entregables`.  
Peek: `analisis_requests.run_progress`; detalle: `analisis_run_stages`.  
Sin resume mid-flight ni payloads de módulos en stages.

## Edges invocadas

Módulos: `multichain-basica`, `compliance-screen`, `analisis-portfolio`, `analisis-multichain`, `analisis-origins`, `analisis-activity`, `analisis-entregables`.

Ensamblado: `analisis-empty-wallet`, `analisis-synthesize`, `analisis-custody`.

## Retry hijas

Hasta 12 intentos ante 429/502/503/**504**/timeouts (espejo Deno). Si agotan → `failed` + `error_message`.

## CLI

```bash
python -m workers.analisis_run.job --limit 5
python -m workers.analisis_run.job --request-id <uuid>
```

`--limit` clamp **1–5** (default 5).

Vault: `12 - Workers/Analisis Run/` · ADR paralelismo/stages en `08 - Decisiones`
