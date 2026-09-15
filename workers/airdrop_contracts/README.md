# airdrop_contracts

Sync de contratos **claim / merkle distributor** de airdrops → `internal.airdrop_contracts`.

Complementa [`token_taxonomy`](../token_taxonomy/) (tag del **token**). Este worker cataloga el **contrato que emite claims** para Origins (`category_percentages.airdrop`).

## Fuentes v1.1 (Envio)

| Fuente | Qué aporta |
|--------|------------|
| `contracts.yaml` | Claim contracts históricos curados (`source=walpulse_curated`) |
| `factories.yaml` + **Sablier Envio GraphQL** | Campaigns Sablier (`source=factory_clone`) — **sin** Alchemy `eth_getLogs` |
| Spellbook `_sector/airdrops/` (path: `dbt_subprojects/daily_spellbook/models/...`) | Metadata / enrichment (token, event ref) — **no** literales claim |

**Fuera de v1:** Galxe, CryptoRank, Dune API.  
**1inch:** el toolkit no tiene factory → filas en `contracts.yaml`.

## Discovery Sablier (Envio)

- Endpoint default: `https://indexer.hyperindex.xyz/508d217/v1/graphql` ([docs](https://docs.sablier.com/api/airdrops/indexers))
- Allowlist: addresses en `factories.yaml`
- Query paginada `Campaign` donde `factory.address _in` allowlist
- Map `chainId` → slug Walpulse (`43114`→`avalanche_c`, …)
- Override: `SABLIER_ENVIO_URL`, `SABLIER_ENVIO_PAGE_SIZE`
- Si Envio falla: fallback a clones ya en BD; curated siempre se mantiene
- **No** usa `ALCHEMY_KEY` / block cursors para discovery

## Destino

- Tabla: `internal.airdrop_contracts`
- Cursors bloque (`airdrop_factory_scan`): legacy / no usados por Envio path
- RPCs: `get/begin/append/commit_airdrop_contracts_*`, `get_airdrop_factory_clone_rows`
- Migraciones: `20260829010000_create_internal_airdrop_contracts`, `20260829020000_airdrop_factory_scan_cursors`

## Local

```powershell
cd C:\Walpulse\workers
pip install -r requirements.txt
$env:SUPABASE_URL = "https://fxocgurmnirxvvkdzuyt.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "<service_role>"

pytest tests/test_airdrop_contracts.py -q

# Curated only
python -m workers.airdrop_contracts.job --skip-factories --skip-spellbook --skip-validate --force

# Envio factories + curated
python -m workers.airdrop_contracts.job
```

## Skip catalog

```
sha256(contracts:<yamlHash>|factories:<yamlHash>|clones:<sortedCloneKeysHash>)
```

## Secrets GHA

| Secret | Uso |
|--------|-----|
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | Ingest |

`ALCHEMY_KEY` **no** es requerido para este worker.

## Disclaimer

Señal de exposición on-chain para Origins — no lista de elegibles ni compliance.

Vault: [[12 - Workers/Airdrop Contracts/Índice]]
