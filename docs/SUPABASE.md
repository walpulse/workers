# Supabase — walpulse/workers

Project ref: `fxocgurmnirxvvkdzuyt`  
API: `https://fxocgurmnirxvvkdzuyt.supabase.co`

Workers usan **PostgREST RPC** con header `apikey` + `Authorization: Bearer <service_role>` (cliente `supabase-py`). No usan `DATABASE_URL` directo en GHA.

## Secrets GHA (repo workers)

| Secret | Uso |
|--------|-----|
| `SUPABASE_URL` | URL del proyecto |
| `SUPABASE_SERVICE_ROLE_KEY` | Llamadas RPC de ingest |
| `GOLDSKY_API_KEY` | Worker `kleros_scout_addresses` (Goldsky private GraphQL; Bearer) |
| `ALCHEMY_KEY` | Worker `airdrop_contracts` (RPC multi-chain factories / eth_getCode) |
| `PINATA_JWT` | Worker `analisis_pdf` (preferido) |
| `PINATA_API_KEY` / `PINATA_API_SECRET` | Worker `analisis_pdf` (fallback) |

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
| `append_mixer_addresses_ingest(p_rows jsonb)` | Insert batch (incl. `privacy_mechanism`, `catalog_tier`) |
| `commit_mixer_addresses_ingest(p_source_hash text)` | Replace live + actualizar sync |

Migraciones: `create_internal_mixer_addresses`, `add_mixer_addresses_privacy_mechanism`, `add_mixer_addresses_catalog_tier` en repo `database`.

Columnas: `privacy_mechanism` (`zk_pool` \| `stealth` \| `fhe_wrapper` \| `tee`) · `catalog_tier` (`canonical` \| `fork`).

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

### `token_taxonomy`

| RPC | Rol |
|-----|-----|
| `get_token_taxonomy_sync_state()` | Resumen última corrida + conteos |
| `begin_token_taxonomy_ingest()` | Truncar staging |
| `append_token_taxonomy_ingest(p_rows jsonb)` | Insert batch |
| `commit_token_taxonomy_ingest(p_source_hash text)` | Replace live + actualizar sync |

Migración: `create_internal_token_taxonomy` en repo `database`.

### `airdrop_contracts`

| RPC | Rol |
|-----|-----|
| `get_airdrop_contracts_sync_state()` | Leer último hash + conteos |
| `begin_airdrop_contracts_ingest()` | Truncar staging |
| `append_airdrop_contracts_ingest(p_rows jsonb)` | Insert batch |
| `commit_airdrop_contracts_ingest(p_source_hash text)` | Replace live + actualizar sync |
| `get_airdrop_factory_scan_cursors()` | Cursors incremental por factory |
| `upsert_airdrop_factory_scan_cursors(p_rows jsonb)` | Avanzar `last_scanned_block` |
| `get_airdrop_factory_clone_rows()` | Clones live para merge sin full rescan |

Migración: `create_internal_airdrop_contracts` + `airdrop_factory_scan_cursors`.

Secret RPC: `ALCHEMY_KEY` (multi-chain). Overrides opcionales `ETH_RPC_URL`, etc.  
Env opcionales worker: `AIRDROP_FACTORY_LOG_CHUNK`, `AIRDROP_FACTORY_BOOTSTRAP_BLOCKS`.  
Habilitar redes en Alchemy app (OP Mainnet = optimism, Scroll, Linea, …).

### `protocol_addresses`

| RPC | Rol |
|-----|-----|
| `get_protocol_addresses_sync_state()` | Leer último hash + conteos (worker + discovered) |
| `begin_protocol_addresses_ingest()` | Truncar staging |
| `append_protocol_addresses_ingest(p_rows jsonb)` | Insert batch |
| `commit_protocol_addresses_ingest(p_source_hash text)` | Replace filas worker; preserva `origin=discovered` |
| `upsert_protocol_address_discovered(p_row jsonb)` | Lazy cache Origins |

Migración: `create_internal_protocol_addresses` en repo `database`.

### `analisis_pdf`

| RPC | Rol |
|-----|-----|
| `list_analisis_requests_pending_pdf(p_limit)` | FIFO candidatas Estándar/Experta |
| `set_analisis_request_pdf_cid(p_id, p_pdf_cid)` | Set idempotente `pdf_cid` |
| `update_analisis_request` | Patch incluye `pdf_cid` |

Migración: `analisis_requests_pdf_cid` en repo `database`.  
Docs BD: [analisis-pdf.md](https://github.com/walpulse/database/blob/main/docs/analisis-pdf.md)

Secrets: `PINATA_JWT`, `PINATA_API_KEY`, `PINATA_API_SECRET`.

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

select privacy_mechanism, protocol, count(*)
from internal.mixer_addresses
group by 1, 2
order by 1, 3 desc;

select catalog_tier, protocol, count(*)
from internal.mixer_addresses
group by 1, 2
order by 1, 3 desc;
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

select * from internal.token_taxonomy_sync;

select unnest(categories) as tag, count(*)
from internal.token_taxonomy
group by 1
order by 2 desc;

select count(*) from internal.token_taxonomy;
```

```sql
select * from internal.airdrop_contracts_sync;

select source, count(*) from internal.airdrop_contracts group by 1;

select blockchain, factory_address, last_scanned_block
from internal.airdrop_factory_scan
order by 1, 2;

select * from internal.protocol_addresses_sync;

select origin, kind, count(*)
from internal.protocol_addresses
group by 1, 2
order by 3 desc;
```

```sql
-- Pending PDF (Estándar / Experta)
select count(*) as pending_pdf
from walpulse.analisis_requests
where pdf_cid is null
  and analisis_cid is not null
  and tier in ('estandar', 'experta')
  and status in ('succeeded', 'succeeded_with_warnings');
```

---

Detalle de tablas: [internal-cex-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-cex-addresses.md) · [internal-ofac-sdn-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-ofac-sdn-addresses.md) · [internal-mixer-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-mixer-addresses.md) · [internal-bridge-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-bridge-addresses.md) · [internal-kleros-scout-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-kleros-scout-addresses.md) · [internal-spellbook-labels.md](https://github.com/walpulse/database/blob/main/docs/internal-spellbook-labels.md) · [internal-sourcify-verified.md](https://github.com/walpulse/database/blob/main/docs/internal-sourcify-verified.md) · [internal-token-taxonomy.md](https://github.com/walpulse/database/blob/main/docs/internal-token-taxonomy.md) · [internal-airdrop-contracts.md](https://github.com/walpulse/database/blob/main/docs/internal-airdrop-contracts.md) · [internal-protocol-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-protocol-addresses.md) · [analisis-pdf.md](https://github.com/walpulse/database/blob/main/docs/analisis-pdf.md)

---

*Actualizado 2026-09-03 (analisis_pdf)*
