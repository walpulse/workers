# airdrop_contracts

Sync de contratos **claim / merkle distributor** de airdrops → `internal.airdrop_contracts`.

Complementa [`token_taxonomy`](../token_taxonomy/) (tag del **token**). Este worker cataloga el **contrato que emite claims** para Origins (`category_percentages.airdrop`).

## Fuentes v1

| Fuente | Qué aporta |
|--------|------------|
| `contracts.yaml` | Claim contracts históricos curados (`source=walpulse_curated`) |
| `factories.yaml` + Alchemy logs | Clones Sablier vía `CreateMerkle*` **incremental** (`source=factory_clone`) |
| Spellbook `_sector/airdrops/` | Metadata / enrichment (token, event ref) — **no** literales claim |

**Fuera de v1:** Galxe, CryptoRank, Dune API.  
**1inch:** el toolkit no tiene factory → filas en `contracts.yaml`.

## Scan incremental (factories)

- Cursors en `internal.airdrop_factory_scan` (`last_scanned_block` por factory).
- Cada corrida: `from = last+1` → `latest` (pocos `eth_getLogs`).
- **Primera vez** (sin cursor): lookback `AIRDROP_FACTORY_BOOTSTRAP_BLOCKS` (default **5000**).
- Chunk adaptativo ante HTTP 400 (Alchemy Free = máx **10** bloques/`getLogs`).
- Clones previos se releen de BD y se mergean con los nuevos.
- `--force`: rescan desde `from_block` YAML — en Free es muy lento; preferí PAYG para backfill histórico.
- Redes **403**: habilitar la chain en el app Alchemy (OP Mainnet / Scroll / Linea, etc.).

## Destino

- Tabla: `internal.airdrop_contracts`
- Cursors: `internal.airdrop_factory_scan`
- RPCs: `get/begin/append/commit_airdrop_contracts_*`, `get/upsert_airdrop_factory_scan_cursors`, `get_airdrop_factory_clone_rows`
- Migraciones: `20260829010000_create_internal_airdrop_contracts`, `20260829020000_airdrop_factory_scan_cursors`

## Local

```powershell
cd C:\Walpulse\workers
pip install -r requirements.txt
$env:SUPABASE_URL = "https://fxocgurmnirxvvkdzuyt.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "<service_role>"
$env:ALCHEMY_KEY = "<alchemy_key>"

pytest tests/test_airdrop_contracts.py -q

# Curated only
python -m workers.airdrop_contracts.job --skip-factories --skip-spellbook --skip-validate --force

# Incremental factories
python -m workers.airdrop_contracts.job --force   # primera vez / full rescan
python -m workers.airdrop_contracts.job           # días siguientes: incremental
```

## Skip catalog

```
sha256(contracts:<yamlHash>|factories:<yamlHash>|clones:<sortedCloneKeysHash>)
```

Los cursors se actualizan **aunque** el catálogo no cambie (para no re-pagar CU).

## Secrets GHA

| Secret | Uso |
|--------|-----|
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | Ingest |
| `ALCHEMY_KEY` | RPC multi-chain (`eth-mainnet`, `opt-mainnet`, …) |

Overrides opcionales: `ETH_RPC_URL`, `OPTIMISM_RPC_URL`, etc. (ganan sobre Alchemy).

## Disclaimer

Señal de exposición on-chain para Origins — no lista de elegibles ni compliance.

Vault: [[12 - Workers/Airdrop Contracts/Índice]]
