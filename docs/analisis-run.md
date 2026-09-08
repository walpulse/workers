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
| Poll | **Live 2026-09-08:** push paths + `workflow_dispatch` + schedule `0 */6 * * *` UTC (loop ~6 h / poll 45 s) |
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

## Hops / lights / sujeto

- **Hops = screening `funder_risk`** (no Origins completo): top fondeadores **globales** (Estándar **2** / Experta **5**), **1 chain dominante** por fondeador, Activity corta (~75 txs / 15d) + IQ. Señales: OFAC, mixer, CEX, bridge, `is_normal_wallet`. Edge: `analisis-origins` `mode=funder_risk` (`analisis-origins` **v12+**).
- Experta **hop-2** solo si hop-1 es wallet normal (`is_normal_wallet`; no cex/bridge/mixer/ofac): hasta **2** fondeadores del hop-1, mismo screen. Skip targets CEX/bridge/mixer/zero/sujeto.
- Hops **no** re-pesan la síntesis (contexto + capa B).
- Skip CEX (label / catálogo) → tarjeta slim con `skipped`, `skip_reason`, `cex_name` en `analisis-v1` (hops y Activity lights). Detalle completo en `evidencia-v1`.
- Fallo HTTP de un hop o light → se registra (`error`) y el run **sigue** (`succeeded_with_warnings` si hubo soft errors).
- Origins/Activity del **sujeto**: **1 chain por HTTP** (`fetch_slice` + partición) → `labels_from` → Origins también `infer_cex_one`×top-N → `score_from` CPU-only → `aggregate_from` (+ `funder_hints`). Soft-fail del módulo solo si 0 chains OK.
- Logs GHA: `origins …` / `activity …` / `funder_risk hop=…` con flush.

Accept / Básica rechazan sujeto CEX con `400 cex_wallet_not_analyzable` (antes de enqueue / sync).

Smoke validado 2026-09-08 (`60e6f975`, Experta ~20 min end-to-end; hops `funder_risk` ~33 s).

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

Vault: `12 - Workers/Analisis Run/` · ADR hops: [[2026-09-08 - Hops funder_risk screening]] · paralelismo: [[2026-09-07 - Analisis run paralelismo 5 y stages]]
