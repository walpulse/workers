# analisis_run — orquestación Estándar / Experta

Worker GHA que **ejecuta** el pipeline async (claim FIFO + secuencia HTTP a Edges).  
No recalcula señales ni grades en Python.

| Campo | Valor |
|-------|--------|
| Código | `workers/analisis_run/` |
| Workflow | `.github/workflows/analisis-run.yml` |
| Claim | `claim_analisis_requests_for_run(1, 12)` |
| Poll | 45 s dentro de ventana ~6 h (`0 */6 * * *`) |
| Secrets | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` |

## Cadena

```
accept → accepted → analisis_run → analisis_pdf → analisis_email
```

## Edges invocadas

Módulos: `multichain-basica`, `compliance-screen`, `analisis-portfolio`, `analisis-multichain`, `analisis-origins`, `analisis-activity`, `analisis-entregables`.

Ensamblado: `analisis-empty-wallet`, `analisis-synthesize`, `analisis-custody`.

## Retry hijas

Hasta 12 intentos ante 429/502/503/**504**/timeouts (espejo Deno). Si agotan → `failed` + `error_message`.

## CLI

```bash
python -m workers.analisis_run.job --limit 1
python -m workers.analisis_run.job --request-id <uuid>
```

Vault: `12 - Workers/Analisis Run/` · ADR `2026-09-07 - Worker analisis_run…`
