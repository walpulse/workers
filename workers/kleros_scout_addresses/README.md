# kleros_scout_addresses

Sincroniza el catálogo estático **Kleros Scout** (Address Tags, Tokens, Contract-Domain / CDN) desde el subgraph propio en **Goldsky** hacia `internal.kleros_scout_addresses`.

## Fuente

| Rol | Detalle |
|-----|---------|
| **Primaria (prod)** | Goldsky privado `walpulse-scout-curate/1.0.0` (gtcr-subgraph, Gnosis/`xdai`) |
| Endpoint | `GOLDSKY_GRAPHQL_URL` o default privado en `job.py` |
| Auth | `Authorization: Bearer $GOLDSKY_API_KEY` |
| Opt-in | `--source graph` (The Graph legacy) / `--source envio` (incompleto; no usar en prod) |

Registries canónicos (lowercase en filtro GraphQL):

| Registry | Address |
|----------|---------|
| Address Tags | `0x66260C69d03837016d88c9877e61e08Ef74C59F2` |
| Tokens | `0xeE1502e29795Ef6C2D60F8D7120596abE3baD990` |
| Contract-Domain (CDN) | `0x957A53A994860BE4750810131d9c876b2f52d6E1` |

## Secrets / env

| Variable | Uso |
|----------|-----|
| `SUPABASE_URL` | Requerido |
| `SUPABASE_SERVICE_ROLE_KEY` | Requerido |
| `GOLDSKY_API_KEY` | Requerido (endpoint privado) |
| `GOLDSKY_GRAPHQL_URL` | Opcional — override del endpoint privado |

## Local

```powershell
$env:SUPABASE_URL="..."
$env:SUPABASE_SERVICE_ROLE_KEY="..."
$env:GOLDSKY_API_KEY="..."
python -m workers.kleros_scout_addresses.job
# Force re-ingest:
python -m workers.kleros_scout_addresses.job --force
```

## Pipeline

1. Fetch paginado `litems` (3 registries Scout) desde Goldsky
2. Fingerprint `(registry, itemID, resolutionTime)` → skip si == sync state
3. Parse CAIP-10 / key0–key3 → filas
4. `begin` → `append` (chunks 500) → `commit` RPC

## Workflow

`.github/workflows/kleros-scout-addresses.yml` — cron diario 10:00 UTC + `workflow_dispatch` (`force`).
