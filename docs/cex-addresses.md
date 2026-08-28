# Worker `cex_addresses`

## Propósito

Mantener en Walpulse el catálogo de **addresses CEX curadas** que Dune publica vía Spellbook, sin depender de la API de Dune.

Uso previsto: lookup de labels CEX en señales Origins/Activity (futuro orquestador). No calcula `cex_quality` ni scores.

## Fuente

Repositorio: https://github.com/duneanalytics/spellbook

Directorio monitoreado (SHA vía GitHub API):

`dbt_subprojects/hourly_spellbook/models/_sector/cex/addresses/`

### Qué se parsea

| Archivo | Formato | `blockchain` en Walpulse |
|---------|---------|--------------------------|
| `chains/cex_evms_addresses.sql` | `(0x…, 'cex', 'distinct', …)` | `evm` (lista compartida EVM) |
| `chains/<chain>/cex_<chain>_addresses.sql` con `VALUES` | `('bitcoin', 'addr', …)` | slug Spellbook (`bitcoin`, `solana`, …) |

### Qué se ignora

- `chains/ethereum/cex_ethereum_addresses.sql` y similares que solo llaman `cex_evms(...)` (mezcla on-chain de Dune).

## Destino (Supabase)

Ver [walpulse/database/docs/internal-cex-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-cex-addresses.md).

## Operación GHA

Workflow: `.github/workflows/cex-addresses.yml`

| Trigger | Comportamiento |
|---------|----------------|
| Cron diario 06:00 UTC | Skip si `source_commit` == HEAD Spellbook |
| `workflow_dispatch` | Igual; input `force=true` re-ingesta |

## Seguridad

- `service_role` solo en secrets del repo workers.
- Schema `internal` no expuesto en PostgREST.
- Umbral: commit falla si `evm` &lt; 1000 filas (evita truncate accidental).

## Código

- Parser: `workers/cex_addresses/parse.py`
- Job: `workers/cex_addresses/job.py`
- Tests: `tests/test_parse.py`
