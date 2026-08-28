# Sourcify verified contracts — Parquet export v2

Sync incremental del export [export.sourcify.dev](https://export.sourcify.dev) hacia `internal.sourcify_verified_addresses`.

## Tablas export ingestadas

1. `contract_deployments` → `internal.sourcify_deployments`
2. `verified_contracts` → `internal.sourcify_verified_addresses` (join SQL en RPC)

## Env

| Variable | Requerido |
|----------|-----------|
| `SUPABASE_URL` | sí |
| `SUPABASE_SERVICE_ROLE_KEY` | sí |

## Local

```powershell
pip install -r requirements.txt
pytest -q tests/test_sourcify_verified_parse.py

# Fixtures locales (sin red):
python -m workers.sourcify_verified.job --local-parquet-dir tests/fixtures/sourcify
```

## Flags

- `--force` — re-ingesta aunque ETag coincida
- `--table contract_deployments|verified_contracts` — limitar tabla
- `--max-runtime-seconds 19800` — presupuesto 5,5 h (default)

## Estados de corrida

| Status | Significado |
|--------|-------------|
| `catch_up_complete` | Sin archivos pendientes |
| `partial_progress` | Quedan archivos; retoma en próxima corrida |
| `error` | Falló un archivo |

## Disclaimer

Señal de source verificado Sourcify — no auditoría ni screening oficial.

`chain_id` se persiste como `bigint` en Supabase (algunos valores del export exceden int32).
