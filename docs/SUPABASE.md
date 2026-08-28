# Supabase — walpulse/workers

Project ref: `fxocgurmnirxvvkdzuyt`  
API: `https://fxocgurmnirxvvkdzuyt.supabase.co`

Workers usan **PostgREST RPC** con header `apikey` + `Authorization: Bearer <service_role>` (cliente `supabase-py`). No usan `DATABASE_URL` directo en GHA.

## Secrets GHA (repo workers)

| Secret | Uso |
|--------|-----|
| `SUPABASE_URL` | URL del proyecto |
| `SUPABASE_SERVICE_ROLE_KEY` | Llamadas RPC de ingest |
| `THE_GRAPH_KEY` | Worker `kleros_scout_addresses` (The Graph gateway; no bloqueante si subgraph NOT INDEXED) |

## RPCs por worker

### `cex_addresses`

| RPC | Rol |
|-----|-----|
| `get_cex_addresses_sync_state()` | Leer último commit + conteos |
| `begin_cex_addresses_ingest()` | Truncar staging |
| `append_cex_addresses_ingest(p_rows jsonb)` | Insert batch |
| `commit_cex_addresses_ingest(p_commit text)` | Replace live + actualizar sync |

Migración: `create_internal_cex_addresses` en repo `database`.

### `ofac_sdn`

| RPC | Rol |
|-----|-----|
| `get_ofac_sdn_addresses_sync_state()` | Leer último hash + conteos |
| `begin_ofac_sdn_addresses_ingest()` | Truncar staging |
| `append_ofac_sdn_addresses_ingest(p_rows jsonb)` | Insert batch |
| `commit_ofac_sdn_addresses_ingest(p_source_hash text, p_list_updated_at date)` | Replace live + actualizar sync |

Migración: `create_internal_ofac_sdn_addresses` en repo `database`.

### `mixer_addresses`

| RPC | Rol |
|-----|-----|
| `get_mixer_addresses_sync_state()` | Leer último hash + conteos |
| `begin_mixer_addresses_ingest()` | Truncar staging |
| `append_mixer_addresses_ingest(p_rows jsonb)` | Insert batch |
| `commit_mixer_addresses_ingest(p_source_hash text)` | Replace live + actualizar sync |

Migración: `create_internal_mixer_addresses` en repo `database`.

### `bridge_addresses`

| RPC | Rol |
|-----|-----|
| `get_bridge_addresses_sync_state()` | Leer último hash + conteos |
| `begin_bridge_addresses_ingest()` | Truncar staging |
| `append_bridge_addresses_ingest(p_rows jsonb)` | Insert batch |
| `commit_bridge_addresses_ingest(p_source_hash text)` | Replace live + actualizar sync |

Migración: `create_internal_bridge_addresses` en repo `database`.

### `kleros_scout_addresses`

| RPC | Rol |
|-----|-----|
| `get_kleros_scout_addresses_sync_state()` | Leer último hash + conteos |
| `begin_kleros_scout_addresses_ingest()` | Truncar staging |
| `append_kleros_scout_addresses_ingest(p_rows jsonb)` | Insert batch |
| `commit_kleros_scout_addresses_ingest(p_source_hash text)` | Replace live + actualizar sync |

Migración: `create_internal_kleros_scout_addresses` en repo `database`.

### `spellbook_labels`

| RPC | Rol |
|-----|-----|
| `get_spellbook_labels_sync_state()` | Leer último hash + conteos |
| `begin_spellbook_labels_ingest()` | Truncar staging |
| `append_spellbook_labels_ingest(p_rows jsonb)` | Insert batch |
| `commit_spellbook_labels_ingest(p_source_hash text)` | Replace live + actualizar sync |

Migración: `create_internal_spellbook_labels` en repo `database`.

### `sourcify_verified`

| RPC | Rol |
|-----|-----|
| `get_sourcify_verified_sync_state()` | Resumen última corrida + conteos |
| `get_sourcify_export_files(p_table)` | Manifest ETag (filtro opcional) |
| `upsert_sourcify_deployments(p_rows jsonb)` | Batch upsert deployments |
| `upsert_sourcify_verified_from_deployments(p_rows jsonb)` | Join deployments + upsert lookup |
| `record_sourcify_export_file(...)` | Marca archivo Parquet ingestado |
| `update_sourcify_verified_sync_run(p_status, p_files_processed)` | Cierra corrida |

Migración: `create_internal_sourcify_verified` + `alter_sourcify_deployments_chain_address` en repo `database`.

## Monitoreo rápido

```sql
select * from internal.cex_addresses_sync;

select blockchain, count(*) 
from internal.cex_addresses 
group by 1 
order by 2 desc 
limit 10;

select * from internal.ofac_sdn_addresses_sync;

select blockchain, count(*)
from internal.ofac_sdn_addresses
group by 1
order by 2 desc
limit 10;

select * from internal.mixer_addresses_sync;

select protocol, contract_role, count(*)
from internal.mixer_addresses
group by 1, 2
order by 3 desc;
```

```sql
select * from internal.bridge_addresses_sync;

select bridge_slug, contract_role, count(*)
from internal.bridge_addresses
group by 1, 2
order by 3 desc
limit 15;

select * from internal.kleros_scout_addresses_sync;

select registry, count(*)
from internal.kleros_scout_addresses
group by 1
order by 2 desc;

select * from internal.spellbook_labels_sync;

select category, count(*)
from internal.spellbook_labels
group by 1
order by 2 desc
limit 10;

select * from internal.sourcify_verified_sync;

select table_name, count(*) from internal.sourcify_export_files group by 1;

select count(*) from internal.sourcify_verified_addresses;
```

---

Detalle de tablas: [internal-cex-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-cex-addresses.md) · [internal-ofac-sdn-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-ofac-sdn-addresses.md) · [internal-mixer-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-mixer-addresses.md) · [internal-bridge-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-bridge-addresses.md) · [internal-kleros-scout-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-kleros-scout-addresses.md) · [internal-spellbook-labels.md](https://github.com/walpulse/database/blob/main/docs/internal-spellbook-labels.md) · [internal-sourcify-verified.md](https://github.com/walpulse/database/blob/main/docs/internal-sourcify-verified.md)
