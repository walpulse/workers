# Worker `token_taxonomy`

Sync taxonomía Walpulse (`stable`, `meme`, `airdrop`, `bluechip`) desde CoinGecko Demo API + DefiLlama stablecoins (v1.1) → `internal.token_taxonomy`.

## Ejecución

```bash
python -m workers.token_taxonomy.job
python -m workers.token_taxonomy.job --force
```

## Env

| Variable | Requerido |
|----------|-----------|
| `SUPABASE_URL` | sí |
| `SUPABASE_SERVICE_ROLE_KEY` | sí |
| `COINGECKO_KEY` | sí (Demo API; header `x-cg-demo-api-key`) |

DefiLlama API y clone `peggedassets-server` no requieren secrets adicionales.

## Pipeline (v1.1)

1. Sparse-clone `DefiLlama/peggedassets-server` → parse `chainContracts` (stable, EVM)
2. `GET stablecoins.llama.fi/stablecoins` + `GET api.llama.fi/chains` (fiat pegs, excl. `peggedVAR`)
3. Hybrid DL: git addresses ∪ CG expand para gecko gaps (reutiliza `/coins/list`)
4. `GET /coins/list?include_platform=true` (1 crédito)
5. `GET /coins/markets?category=…` × 12 categorías (~39 créditos)
6. `GET /coins/markets?order=market_cap_desc` top-100 bluechip (1 crédito)
7. Merge union CoinGecko ∪ DefiLlama por `(chain_id, address)`
8. Skip si `source_hash` igual; else replace vía RPCs ingest

**~42 créditos/sync** CoinGecko · cron diario 12:00 UTC.

**Fingerprint:** SHA-256 de categorías CG + bluechip + `defillama:<commit>` + hash API stablecoins list.

## Tests

```bash
pytest tests/test_token_taxonomy_parse.py tests/test_token_taxonomy_defillama_parse.py -q
```

Vault: [[12 - Workers/Token Taxonomy/Índice]] · BD: [internal-token-taxonomy.md](https://github.com/walpulse/database/blob/main/docs/internal-token-taxonomy.md)
