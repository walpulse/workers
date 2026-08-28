# Worker `token_taxonomy`

Sync taxonomía Walpulse (`stable`, `meme`, `airdrop`, `bluechip`) desde CoinGecko Demo API → `internal.token_taxonomy`.

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

## Pipeline

1. `GET /coins/list?include_platform=true` (1 crédito)
2. `GET /coins/markets?category=…` × 12 categorías (~39 créditos)
3. `GET /coins/markets?order=market_cap_desc` top-100 bluechip (1 crédito)
4. Expand `(gecko_id, platform)` → `(chain_id, address)` vía mapa estático
5. Skip si `source_hash` igual; else replace vía RPCs ingest

**~42 créditos/sync** · cron diario 12:00 UTC.

## Tests

```bash
pytest tests/test_token_taxonomy_parse.py -q
```

Vault: [[12 - Workers/Token Taxonomy/Índice]] · BD: [internal-token-taxonomy.md](https://github.com/walpulse/database/blob/main/docs/internal-token-taxonomy.md)
