# Supabase — walpulse/workers

Project ref: `fxocgurmnirxvvkdzuyt`  
API: `https://fxocgurmnirxvvkdzuyt.supabase.co`

Workers usan **PostgREST RPC** con header `apikey` + `Authorization: Bearer <service_role>` (cliente `supabase-py`). No usan `DATABASE_URL` directo en GHA.

## Secrets GHA (repo workers)

| Secret | Uso |
|--------|-----|
| `SUPABASE_URL` | URL del proyecto |
| `SUPABASE_SERVICE_ROLE_KEY` | Llamadas RPC de ingest |

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
```

---

Detalle de tablas: [internal-cex-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-cex-addresses.md) · [internal-ofac-sdn-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-ofac-sdn-addresses.md)
