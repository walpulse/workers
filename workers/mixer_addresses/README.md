# mixer_addresses

Sync diario de contratos mixer/privacy (pools + routers/entrypoints) a `internal.mixer_addresses`.

## Fuentes

| Fuente | URL / path |
|--------|------------|
| Tornado Cash docs | `tornadocash/docs` → `general/tornado-cash-smart-contracts.md` |
| L2BEAT Privacy | `l2beat/l2beat` → `packages/config/src/projects/{slug}/discovered.json` |
| Railgun deployments | `Railgun-Community/deployments` → `src/chains/{ethereum,arbitrum,polygon,bsc}.ts` (proxy) |
| Cyclone docs | https://docs.cyclone.xyz/deployment — Anonymity Pools (EVM) |
| Typhoon seed | `data/typhoon_seed.json` (omitido si &lt;3 pools verificables) |

Proyectos L2BEAT: `cloaked`, `privacy-pools`, `railgun`, `strk20`, `tornado-cash`, `umbra`, `privacy-boost`, `zama-cw`.

## Destino

- Tabla: `internal.mixer_addresses`
- RPCs: `get/begin/append/commit_mixer_addresses_*`
- Migraciones: `create_internal_mixer_addresses`, `add_mixer_addresses_privacy_mechanism`, `add_mixer_addresses_catalog_tier`

## Taxonomía

### `privacy_mechanism`

| Valor | Protocolos |
|-------|------------|
| `zk_pool` | tornado-cash, privacy-pools, railgun, strk20, cyclone |
| `stealth` | umbra, cloaked |
| `fhe_wrapper` | zama-cw |
| `tee` | privacy-boost |

### `catalog_tier`

| Valor | Protocolos |
|-------|------------|
| `canonical` | tornado-cash, privacy-pools, railgun, strk20, umbra, cloaked, zama-cw, privacy-boost |
| `fork` | cyclone (typhoon-cash cuando el seed tenga ≥3 pools) |

Catalog-only — Origins filtrará después.

## Local

```powershell
cd C:\Walpulse\workers
$env:SUPABASE_URL = "https://fxocgurmnirxvvkdzuyt.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "<service_role>"

python -m pytest tests/test_mixer_parse.py -q
python -m workers.mixer_addresses.job
python -m workers.mixer_addresses.job --force
```

## Skip

Fingerprint compuesto SHA-256 incluye Tornado commit, L2BEAT configHashes, Railgun deployments commit, Cyclone docs hash, Typhoon seed hash (si existe).

## Disclaimer

Señal de exposición on-chain — no screening oficial ni determinación de compliance.

Vault: [[12 - Workers/Mixer Addresses/Índice]]
