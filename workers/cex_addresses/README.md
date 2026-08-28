# Worker `cex_addresses`

Sincroniza el catálogo CEX curado de [Dune Spellbook](https://github.com/duneanalytics/spellbook) a `internal.cex_addresses`.

## Ejecución

```bash
python -m workers.cex_addresses.job
python -m workers.cex_addresses.job --force
python -m workers.cex_addresses.job --spellbook-dir /path/to/cex/addresses
```

## Env

| Variable | Requerido |
|----------|-----------|
| `SUPABASE_URL` | sí |
| `SUPABASE_SERVICE_ROLE_KEY` | sí |
| `GITHUB_TOKEN` | opcional (API commits; GHA lo inyecta) |

## Archivos

| Archivo | Rol |
|---------|------|
| `job.py` | SHA check, clone, ingest RPCs |
| `parse.py` | Regex VALUES de `cex_evms_addresses.sql` + seeds por chain |

## Tests

```bash
pytest tests/test_parse.py -q
```

Vault: [[12 - Workers/CEX Addresses/Índice]]
