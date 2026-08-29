# protocol_addresses

Sync de contratos DeFi (factory/router/lending/aggregator/…) a `internal.protocol_addresses`.

## Capas

| Capa | Flag | Fuente | `origin` |
|------|------|--------|----------|
| P0 | `--layers p0` (default) | `data/official_seed.json` address books | `official` |
| P1 | `--layers p0,p1` | Spellbook VALUES (`labels/addresses`) | `spellbook` |
| P2 | `--layers p0,p1,p2` | DefiLlama-Adapters allowlist | `defillama` |

**No** guarda pools LP. Factories/routers/registries. LI.FI/Socket → `kind=aggregator`.

Lazy cache Origins: RPC `upsert_protocol_address_discovered` (`origin=discovered`).

## Destino

- Tabla: `internal.protocol_addresses`
- RPCs: `get/begin/append/commit_protocol_addresses_*` + `upsert_protocol_address_discovered`
- Migración: `20260829200000_create_internal_protocol_addresses`

## Local

```powershell
cd C:\Walpulse\workers
$env:SUPABASE_URL = "https://fxocgurmnirxvvkdzuyt.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "<service_role>"

pytest tests/test_protocol_addresses_parse.py -q
python -m workers.protocol_addresses.job
python -m workers.protocol_addresses.job --force
python -m workers.protocol_addresses.job --layers p0,p1 --spellbook-dir tests/fixtures/spellbook_labels
```

## GHA

- Workflow: `.github/workflows/protocol-addresses.yml`
- Cron: **13:00 UTC** (default `--layers p0`)
- Dispatch: `force`, `layers` (`p0` / `p0,p1` / `p0,p1,p2`)
- Secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`

## Skip

Fingerprint compuesto SHA-256 de capas activas (`official:<seed_sha>|spellbook:<commit>|…`).

Merge: `official` > `spellbook` > `defillama`.

## Disclaimer

Señal de tipología de contrato on-chain — no screening oficial ni determinación de compliance.

Vault: [[12 - Workers/Protocol Addresses/Índice]]
ADR: [[2026-08-28 - Worker protocol addresses capas P0 P1 P2]]
