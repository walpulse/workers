# Kleros Scout — address tags

Sync diario del catálogo **Kleros Scout** (Address Tags, Tokens, Contract-Domain) desde The Graph → `internal.kleros_scout_addresses`.

**Disclaimer:** label de contraparte — *presente en registro curado Kleros Scout*. No verificación oficial ni screening.

## Fuente

| Campo | Valor |
|-------|--------|
| Subgraph | `legacy-curate-gnosis` |
| ID | `9hHo5MpjpC1JqfD3BsgFnojGurXRHTrHWcUcZPPCo6m8` |
| Fallback | Envio `https://indexer.hyperindex.xyz/1a2f51c/v1/graphql` |
| Portal | [scout-app.kleros.io](https://scout-app.kleros.io/home) |

## Env

| Variable | Requerida |
|----------|-----------|
| `SUPABASE_URL` | sí |
| `SUPABASE_SERVICE_ROLE_KEY` | sí |
| `THE_GRAPH_KEY` | sí (Graph primario); omitir con `--source envio` o `--fixture-json` |

## Local

```powershell
cd C:\Walpulse\workers
pip install -r requirements.txt
pytest tests/test_kleros_scout_parse.py -q

# Ingest vía Envio (sin Graph key)
python -m workers.kleros_scout_addresses.job --source envio

# Ingest vía The Graph
python -m workers.kleros_scout_addresses.job

# Fixture (requiere ≥1000 filas para commit — usar solo parse tests)
python -m workers.kleros_scout_addresses.job --fixture-json tests/fixtures/kleros_scout_sample.json

# Forzar re-ingest
python -m workers.kleros_scout_addresses.job --force
```

## Pipeline

1. Fetch paginado 3 registros TCR (Graph; fallback Envio si Graph falla)
2. Fingerprint → comparar con `kleros_scout_addresses_sync.source_hash`
3. Parse CAIP / key0–key3 → filas normalizadas
4. RPC: `begin` → `append` (500) → `commit`

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
