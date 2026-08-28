# walpulse/workers

Workers batch en **Python 3.12** ejecutados desde **GitHub Actions**. Escriben en Supabase Walpulse (`fxocgurmnirxvvkdzuyt`) vía RPC `service_role` — no exponen el schema `internal`.

**Agentes:** leer [AGENTS.md](AGENTS.md) · [docs/PROCESSES.md](docs/PROCESSES.md) · bóveda `12 - Workers`.

Prod Supabase: `fxocgurmnirxvvkdzuyt`. Secrets en GitHub Actions: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

## Workers

| Worker | Workflow | Fuente | Destino | Cron UTC |
|--------|----------|--------|---------|----------|
| `cex_addresses` | [cex-addresses.yml](.github/workflows/cex-addresses.yml) | [Dune Spellbook](https://github.com/duneanalytics/spellbook) (VALUES curados) | `internal.cex_addresses` | 06:00 |
| `ofac_sdn` | [ofac-sdn.yml](.github/workflows/ofac-sdn.yml) | OFAC SDN Advanced ZIP | `internal.ofac_sdn_addresses` | 07:00 |
| `mixer_addresses` | [mixer-addresses.yml](.github/workflows/mixer-addresses.yml) | Tornado Cash docs + L2BEAT Privacy | `internal.mixer_addresses` (+ `privacy_mechanism`) | 08:00 |
| `bridge_addresses` | [bridge-addresses.yml](.github/workflows/bridge-addresses.yml) | DefiLlama bridges-server + registros oficiales | `internal.bridge_addresses` | 09:00 |

Catálogo operativo: [docs/PROCESSES.md](docs/PROCESSES.md). README por worker en `workers/<name>/README.md`.

### Patrón común (reference sync)

1. Leer estado sync (`get_*_sync_state`) — skip si fingerprint/commit/hash sin cambios.
2. Parsear fuente externa → filas normalizadas.
3. `begin_*_ingest` → `append_*` (chunks 500) → `commit_*_ingest` (replace atómico + umbral mínimo de filas).

### Disclaimers

- **OFAC SDN**, **mixer_addresses** y **bridge_addresses:** señal de exposición on-chain — no screening oficial ni determinación de compliance.

## Secrets (repo `walpulse/workers`)

| Secret | Valor |
|--------|--------|
| `SUPABASE_URL` | `https://fxocgurmnirxvvkdzuyt.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | service role del proyecto Walpulse |

`GITHUB_TOKEN` lo provee Actions (API de commits / rate limits).

## Local

```powershell
cd C:\Walpulse\workers
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q

$env:SUPABASE_URL = "https://fxocgurmnirxvvkdzuyt.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "<service_role>"

python -m workers.cex_addresses.job
python -m workers.ofac_sdn.job
python -m workers.mixer_addresses.job
python -m workers.bridge_addresses.job

# Forzar re-ingest
python -m workers.mixer_addresses.job --force
python -m workers.bridge_addresses.job --force
```

## Docs (repo)

- [AGENTS.md](AGENTS.md) — entrada agentes
- [docs/PROCESSES.md](docs/PROCESSES.md) — catálogo de jobs
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/SUPABASE.md](docs/SUPABASE.md)
- [docs/cex-addresses.md](docs/cex-addresses.md)

Schema BD: repo [walpulse/database](https://github.com/walpulse/database) → `docs/internal-*.md`.

## Atribución

- CEX: [duneanalytics/spellbook](https://github.com/duneanalytics/spellbook). Walpulse no republica el SQL.
- OFAC: [Sanctions List Service](https://sanctionslist.ofac.treas.gov/Home/SdnList). Subset parseado en Postgres propio.
- Mixer: [tornadocash/docs](https://github.com/tornadocash/docs) + [L2BEAT Privacy discovery](https://github.com/l2beat/l2beat). Pools/routers/entrypoints filtrados.
- Bridge: [DefiLlama bridges-server](https://github.com/DefiLlama/bridges-server) + Stargate/Wormhole/CCIP/Across/Axelar/Hop. Gateways filtrados (no agregadores LI.FI/Socket).
