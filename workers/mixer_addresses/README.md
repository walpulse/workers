# mixer_addresses

Sync diario de contratos mixer/privacy (pools + routers/entrypoints) a `internal.mixer_addresses`.

## Fuentes

| Fuente | URL / path |
|--------|------------|
| Tornado Cash docs | `tornadocash/docs` → `general/tornado-cash-smart-contracts.md` |
| L2BEAT Privacy | `l2beat/l2beat` → `packages/config/src/projects/{slug}/discovered.json` |

Proyectos L2BEAT: `cloaked`, `privacy-pools`, `railgun`, `strk20`, `tornado-cash`, `umbra`, `privacy-boost`, `zama-cw`.

## Destino

- Tabla: `internal.mixer_addresses`
- RPCs: `get/begin/append/commit_mixer_addresses_*`
- Migración: `20260828100000_create_internal_mixer_addresses`

## Local

```powershell
cd C:\Walpulse\workers
$env:SUPABASE_URL = "https://fxocgurmnirxvvkdzuyt.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "<service_role>"

pytest tests/test_mixer_parse.py -q
python -m workers.mixer_addresses.job
python -m workers.mixer_addresses.job --force
python -m workers.mixer_addresses.job --tornado-md-path tests/fixtures/tornado_docs_sample.md
```

Opcional: `$env:GITHUB_TOKEN` para GitHub commits API (rate limit).

## Skip

Fingerprint compuesto SHA-256:

```
sha256(tornado-docs:<commit>|cloaked:<configHash>|…|zama-cw:<configHash>)
```

`strk20` no tiene `discovered.json` — dirección de pool hardcodeada desde config L2BEAT.

## Disclaimer

Señal de exposición on-chain — no screening oficial ni determinación de compliance.

Vault: [[12 - Workers/Mixer Addresses/Índice]]
