# OFAC SDN — wallets sancionadas

Sync diario del catálogo **OFAC SDN Advanced** (`Digital Currency Address`) → `internal.ofac_sdn_addresses`.

**Disclaimer:** señal de exposición on-chain para Walpulse — no screening oficial.

## Fuente

| Campo | Valor |
|-------|--------|
| URL | `https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ADVANCED.ZIP` |
| Formato | SDN Advanced XML |
| Portal | [sanctionslist.ofac.treas.gov/Home/SdnList](https://sanctionslist.ofac.treas.gov/Home/SdnList) |

## Env

| Variable | Requerida |
|----------|-----------|
| `SUPABASE_URL` | sí |
| `SUPABASE_SERVICE_ROLE_KEY` | sí |

## Local

```powershell
cd C:\Walpulse\workers
pip install -r requirements.txt
pytest tests/test_ofac_parse.py -q

# Con XML ya descargado
python -m workers.ofac_sdn.job --xml-path C:\path\to\SDN_ADVANCED.XML

# Descarga + ingest
python -m workers.ofac_sdn.job

# Forzar re-ingest
python -m workers.ofac_sdn.job --force
```

## Pipeline

1. Descargar ZIP (o usar `--xml-path`)
2. SHA-256 → comparar con `ofac_sdn_addresses_sync.source_hash`
3. Parse `Digital Currency Address - *` + metadatos entidad/programa
4. RPC: `begin` → `append` (500) → `commit`

## Prod (2026-08-28)

Primer ingest OK vía push a `main` → [GHA run 33134124168](https://github.com/walpulse/workers/actions/runs/33134124168).

| Métrica | Valor |
|---------|--------|
| Filas | 995 |
| EVM | 125 |
| OFAC list date | 2026-08-26 |

## Monitoreo

```sql
select * from internal.ofac_sdn_addresses_sync;

select blockchain, count(*)
from internal.ofac_sdn_addresses
group by 1 order by 2 desc;
```

## Relacionado

- BD: `walpulse/database/docs/internal-ofac-sdn-addresses.md`
- Workflow: `.github/workflows/ofac-sdn.yml`
- Vault: `12 - Workers/OFAC SDN/`
