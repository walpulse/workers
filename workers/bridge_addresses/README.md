# bridge_addresses

Sync diario de contratos gateway bridge a `internal.bridge_addresses`.

## Fuentes

| Fuente | URL / path |
|--------|------------|
| DefiLlama bridges-server | `DefiLlama/bridges-server` → `src/adapters/*/index.ts` + `src/data/bridgeNetworkData.ts` |
| Stargate / LayerZero | `mainnet.stargate-api.com/v1/metadata?version=v2` |
| Wormhole | `wormhole-foundation/wormhole` → `sdk/js/src/utils/consts.ts` (MAINNET) |
| Hop | `bridges-server` adapter hop (`contractAddresses`) |
| Chainlink CCIP | `docs.chain.link/api/ccip/v1/chains?environment=mainnet` |
| Across | `across-protocol/contracts` → `broadcast/deployed-addresses.json` |
| Axelar | `axelar-mainnet.s3.../mainnet-config-1.x.json` |

**Excluido v1:** LI.FI, Socket (routers agregadores), DefiLlama Pro.

## Destino

- Tabla: `internal.bridge_addresses`
- RPCs: `get/begin/append/commit_bridge_addresses_*`
- Migración: `20260828110000_create_internal_bridge_addresses`

## Local

```powershell
cd C:\Walpulse\workers
$env:SUPABASE_URL = "https://fxocgurmnirxvvkdzuyt.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "<service_role>"

pytest tests/test_bridge_parse.py -q
python -m workers.bridge_addresses.job
python -m workers.bridge_addresses.job --force
python -m workers.bridge_addresses.job --defillama-dir tests/fixtures/defillama_sample `
  --stargate-json-path tests/fixtures/stargate_metadata_sample.json `
  --wormhole-consts-path tests/fixtures/wormhole_consts_sample.ts `
  --hop-adapter-path tests/fixtures/hop_adapter_sample.ts `
  --ccip-json-path tests/fixtures/ccip_chains_sample.json `
  --across-json-path tests/fixtures/across_addresses_sample.json `
  --axelar-json-path tests/fixtures/axelar_config_sample.json
```

Opcional: `$env:GITHUB_TOKEN` para GitHub commits API (rate limit).

## Skip

Fingerprint compuesto SHA-256:

```
sha256(defillama:<commit>|stargate:<hash>|wormhole:<hash>|hop:<hash>|ccip:<hash>|across:<hash>|axelar:<hash>)
```

Merge: prioridad oficial (Across, CCIP, Stargate, Wormhole, Hop, Axelar) > DefiLlama.

## Disclaimer

Señal de exposición on-chain — no screening oficial ni determinación de compliance.

Vault: [[12 - Workers/Bridge Addresses/Índice]]
