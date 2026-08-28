# Worker `spellbook_labels`

Sincroniza labels **estáticos** curados de [Dune Spellbook](https://github.com/duneanalytics/spellbook) a `internal.spellbook_labels`.

**Incluye:** VALUES en `labels/addresses` + CEX mapeado desde `cex/addresses`.  
**No incluye:** labels `source='query'` de Dune (`labels.addresses` completo).

## Ejecución

```bash
python -m workers.spellbook_labels.job
python -m workers.spellbook_labels.job --force
python -m workers.spellbook_labels.job --spellbook-dir /path/with/labels/addresses+cex/addresses
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
| `job.py` | Fingerprint compuesto, sparse-clone, ingest RPCs |
| `parse.py` | VALUES labels + mapeo CEX → schema labels |

## Tests

```bash
pytest tests/test_spellbook_labels_parse.py -q
```

## Prod (2026-08-28)

9.363 filas · hash `57735ae7f7f5f33…` · GHA [33142465039](https://github.com/walpulse/workers/actions/runs/33142465039)

Vault: [[12 - Workers/Spellbook Labels/Índice]] · Docs: [docs/spellbook-labels.md](../../docs/spellbook-labels.md)
