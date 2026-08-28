# Kleros Scout — address tags

Sync diario del catálogo **Kleros Scout** (Address Tags, Tokens, Contract-Domain) hacia `internal.kleros_scout_addresses`.

**Disclaimer:** label de contraparte — *presente en registro curado Kleros Scout*. No verificación oficial ni screening.

## Fuente

| Campo | Valor |
|-------|--------|
| **Operativa (ago 2026)** | Envio HyperIndex — `https://indexer.hyperindex.xyz/1a2f51c/v1/graphql` |
| The Graph (primario en código) | `legacy-curate-gnosis` — ID `9hHo5MpjpC1JqfD3BsgFnojGurXRHTrHWcUcZPPCo6m8` |
| Estado Graph (ago 2026) | **NOT INDEXED** — gateway responde `subgraph not found: no allocations` |
| Portal Scout | [scout-app.kleros.io](https://scout-app.kleros.io/home) |

El job intenta The Graph primero; si falla (como hoy), usa Envio automáticamente. Misma proyección de filas en ambos backends.

## Env

| Variable | Requerida |
|----------|-----------|
| `SUPABASE_URL` | sí |
| `SUPABASE_SERVICE_ROLE_KEY` | sí |
| `THE_GRAPH_KEY` | no bloqueante — necesaria solo si Graph vuelve a indexar; omitir con `--source envio` |

## Local

```powershell
cd C:\Walpulse\workers
pip install -r requirements.txt
pytest tests/test_kleros_scout_parse.py -q

# Ingest vía Envio (recomendado mientras Graph esté NOT INDEXED)
python -m workers.kleros_scout_addresses.job --source envio

# Ingest intentando Graph primero (fallback Envio automático)
python -m workers.kleros_scout_addresses.job

# Forzar re-ingest
python -m workers.kleros_scout_addresses.job --force
```

## Pipeline

1. Fetch paginado 3 registros TCR (Graph → fallback Envio si `no allocations` u otro error)
2. Fingerprint → comparar con `kleros_scout_addresses_sync.source_hash`
3. Parse CAIP / key0–key3 → filas normalizadas (solo `eip155:*` en v1)
4. RPC: `begin` → `append` (500) → `commit`

## Prod (2026-08-28)

Primer ingest OK vía push a `main` → [GHA run 33140546446](https://github.com/walpulse/workers/actions/runs/33140546446).

| Métrica | Valor |
|---------|--------|
| Filas | 12.504 |
| Fuente efectiva | Envio (Graph falló: no allocations) |
| Hash | `74a0fc220c7f01a2…` |
| Por registry | address_tag 8.024 · contract_domain 3.228 · token 1.252 |

## Monitoreo

```sql
select * from internal.kleros_scout_addresses_sync;

select registry, count(*)
from internal.kleros_scout_addresses
group by 1
order by 2 desc;
```

## Relacionado

- BD: `walpulse/database/docs/internal-kleros-scout-addresses.md`
- Workflow: `.github/workflows/kleros-scout-addresses.yml`
- Vault: `12 - Workers/Kleros Scout/`
- ADR: `2026-08-28 - Worker Kleros Scout address tags The Graph`
