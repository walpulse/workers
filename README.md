# walpulse/workers

Workers batch en **Python 3.12** ejecutados desde **GitHub Actions**. Escriben en Supabase Walpulse (`fxocgurmnirxvvkdzuyt`) vía RPC `service_role` — no exponen el schema `internal`.

**Agentes:** leer [AGENTS.md](AGENTS.md) · [docs/PROCESSES.md](docs/PROCESSES.md) · bóveda `12 - Workers`.

Prod Supabase: `fxocgurmnirxvvkdzuyt`. Secrets en GitHub Actions: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

## Workers

| Worker | Workflow | Fuente | Destino |
|--------|----------|--------|---------|
| `cex_addresses` | [cex-addresses.yml](.github/workflows/cex-addresses.yml) | [Dune Spellbook](https://github.com/duneanalytics/spellbook) (listas VALUES curadas) | `internal.cex_addresses` |

### cex_addresses

1. Consulta el **último commit** que tocó `dbt_subprojects/hourly_spellbook/models/_sector/cex/addresses/` en `main`.
2. Compara con `internal.cex_addresses_sync.source_commit` (RPC `get_cex_addresses_sync_state`).
3. Si es igual → **exit 0 sin ingestar** (cron diario barato).
4. Si cambió → sparse-clone Spellbook, parsea VALUES (`cex_evms_addresses.sql` + seeds no-EVM), replace atómico vía RPCs `begin_` / `append_` / `commit_cex_addresses_ingest`.

No usa Dune API. No parsea wrappers `cex_evms()` (descubrimientos on-chain de Dune).

Detalle BD: repo [walpulse/database](https://github.com/walpulse/database) → `docs/internal-cex-addresses.md`.  
Vault: [[12 - Workers/CEX Addresses/Índice]].

## Secrets (repo `walpulse/workers`)

| Secret | Valor |
|--------|--------|
| `SUPABASE_URL` | `https://fxocgurmnirxvvkdzuyt.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | service role del proyecto Walpulse |

`GITHUB_TOKEN` lo provee Actions (API de commits de Spellbook).

## Local

```powershell
cd C:\Walpulse\workers
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q

# Ingest (requiere env)
$env:SUPABASE_URL = "https://fxocgurmnirxvvkdzuyt.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "<service_role>"
python -m workers.cex_addresses.job

# Forzar re-ingest del mismo commit Spellbook
python -m workers.cex_addresses.job --force

# Parse local sin clone (path a …/cex/addresses)
python -m workers.cex_addresses.job --spellbook-dir "C:\tmp\spellbook\dbt_subprojects\hourly_spellbook\models\_sector\cex\addresses"
```

## Docs (repo)

- [AGENTS.md](AGENTS.md) — entrada agentes
- [docs/PROCESSES.md](docs/PROCESSES.md) — catálogo de jobs
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/SUPABASE.md](docs/SUPABASE.md)
- [docs/cex-addresses.md](docs/cex-addresses.md)

## Atribución

Listado CEX mantenido por Dune en [spellbook](https://github.com/duneanalytics/spellbook). Walpulse no republica el SQL; solo sincroniza el snapshot a Postgres propio.
