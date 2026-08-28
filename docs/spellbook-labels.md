# Worker `spellbook_labels`

## Propósito

Mantener en Walpulse un catálogo de **labels on-chain estáticos** curados en Dune Spellbook, sin depender de la API de Dune.

Uso previsto: lookup unificado de labels en Origins/Activity (futuro orquestador). No replica `labels.addresses` completo (excluye modelos `source='query'`).

## Fuente

Repositorio: https://github.com/duneanalytics/spellbook

Directorios monitoreados (SHA vía GitHub Commits API → fingerprint compuesto):

| Path | Rol |
|------|-----|
| `dbt_subprojects/daily_spellbook/models/_sector/labels/addresses` | VALUES inline (stablecoins, bridges, …) |
| `dbt_subprojects/hourly_spellbook/models/_sector/cex/addresses` | Mapeo institution/CEX → schema labels |

Fingerprint: `sha256(labels_commit + ":" + cex_commit)`.

### Qué se parsea

- Archivos SQL con bloque `VALUES` bajo `labels/addresses/` (excluye unions y modelos query).
- Filas CEX vía `collect_cex_rows()` → `category=institution`, `model_name=cex_{chain}`.

### Qué se ignora

- Unions (`labels_dex.sql`, `labels_bridges.sql`, …).
- Modelos query (`labels_contracts.sql`, dex traders, tornado personas, …).
- SQL `labels_cex_*.sql` (sustituido por mapeo directo desde `cex/addresses`).

## Destino (Supabase)

Ver [walpulse/database/docs/internal-spellbook-labels.md](https://github.com/walpulse/database/blob/main/docs/internal-spellbook-labels.md).

## Operación GHA

Workflow: `.github/workflows/spellbook-labels.yml`

| Trigger | Comportamiento |
|---------|----------------|
| Cron diario 11:00 UTC | Skip si fingerprint == `spellbook_labels_sync.source_hash` |
| `workflow_dispatch` | Igual; input `force=true` re-ingesta |
| Push `main` | Sync si fingerprint cambió |

## Prod (2026-08-28)

| Métrica | Valor |
|---------|--------|
| Filas live | 9.363 |
| Hash | `57735ae7f7f5f33ddfedb2f3d91789638e9b318bbfa7561a7b559fb81356d642` |
| Primer ingest GHA | [run 33142465039](https://github.com/walpulse/workers/actions/runs/33142465039) |

Por categoría: institution 8.120 · dao 483 · infrastructure 443 · bridge 279 · ofac_sanction 38.

## Seguridad

- `service_role` solo en secrets del repo workers.
- Schema `internal` no expuesto en PostgREST.
- Umbral: commit falla si total &lt; 500 filas.

## Código

- Parser: `workers/spellbook_labels/parse.py`
- Job: `workers/spellbook_labels/job.py`
- Tests: `tests/test_spellbook_labels_parse.py`
