# Procesos — walpulse/workers

Catálogo de jobs batch. Detalle operativo en bóveda `12 - Workers/` y README de cada worker.

## Live

### 1. `cex_addresses` — Catálogo CEX desde Spellbook

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/cex-addresses.yml` |
| Código | `workers/cex_addresses/` |
| Fuente | `duneanalytics/spellbook` → `…/cex/addresses/` (VALUES) |
| Destino | `internal.cex_addresses` |
| Trigger | Push `main`, cron diario 06:00 UTC, `workflow_dispatch` (+ `force`) |
| Skip | SHA del path Spellbook == `cex_addresses_sync.source_commit` |

**Pipeline:** GitHub API (último commit del path) → comparar sync state → sparse-clone → parse VALUES → `begin_cex_addresses_ingest` → `append_*` (chunks 500) → `commit_cex_addresses_ingest`.

**No incluye:** wrappers `cex_evms()` (addresses inferidas on-chain por Dune).

Vault: [[12 - Workers/CEX Addresses/Índice]]  
BD: [internal-cex-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-cex-addresses.md)  
ADR: [[2026-08-28 - Worker CEX addresses desde Spellbook]]

### 2. `ofac_sdn` — Wallets sancionadas OFAC SDN

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/ofac-sdn.yml` |
| Código | `workers/ofac_sdn/` |
| Fuente | OFAC SDN Advanced ZIP (`Digital Currency Address`) |
| Destino | `internal.ofac_sdn_addresses` |
| Trigger | Push `main`, cron diario 07:00 UTC, `workflow_dispatch` (+ `force`) |
| Skip | SHA-256 del ZIP == `ofac_sdn_addresses_sync.source_hash` |

**Pipeline:** download ZIP → hash → parse XML → `begin_ofac_sdn_addresses_ingest` → `append_*` (chunks 500) → `commit_ofac_sdn_addresses_ingest`.

**Disclaimer:** señal de exposición on-chain — no screening oficial.

Vault: [[12 - Workers/OFAC SDN/Índice]]  
BD: [internal-ofac-sdn-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-ofac-sdn-addresses.md)  
ADR: [[2026-08-28 - Worker OFAC SDN addresses]]  
GHA (1er ingest): https://github.com/walpulse/workers/actions/runs/33134124168

### 3. `mixer_addresses` — Catálogo mixer/privacy

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/mixer-addresses.yml` |
| Código | `workers/mixer_addresses/` |
| Fuente | Tornado Cash docs + L2BEAT Privacy `discovered.json` (8 protocolos) |
| Destino | `internal.mixer_addresses` |
| Trigger | Push `main`, cron diario 08:00 UTC, `workflow_dispatch` (+ `force`) |
| Skip | SHA-256 compuesto (Tornado commit + L2BEAT configHashes) == `mixer_addresses_sync.source_hash` |

**Pipeline:** fetch Tornado markdown + L2BEAT discoveries → parse pools/routers/entrypoints → `begin_mixer_addresses_ingest` → `append_*` (chunks 500) → `commit_mixer_addresses_ingest`.

**Incluye:** Tornado Classic pools (L1/L2), TornadoRouter, Nova pool; Privacy Pools, Railgun, Umbra, Privacy Boost, Zama wrappers, STRK-20 pool.

**Disclaimer:** señal de exposición on-chain — no screening oficial.

Vault: [[12 - Workers/Mixer Addresses/Índice]]  
BD: [internal-mixer-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-mixer-addresses.md)  
ADR: [[2026-08-28 - Worker mixer addresses Tornado L2BEAT]]  
GHA (1er ingest): https://github.com/walpulse/workers/actions/runs/33136022223

### 4. `bridge_addresses` — Catálogo gateway bridges

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/bridge-addresses.yml` |
| Código | `workers/bridge_addresses/` |
| Fuente | DefiLlama bridges-server + Stargate API + Wormhole consts + Hop adapter + CCIP API + Across contracts + Axelar config |
| Destino | `internal.bridge_addresses` |
| Trigger | Push `main`, cron diario 09:00 UTC, `workflow_dispatch` (+ `force`) |
| Skip | SHA-256 compuesto (DefiLlama commit + hashes fuentes oficiales) == `bridge_addresses_sync.source_hash` |

**Pipeline:** sparse-clone bridges-server → fetch APIs/docs oficiales → parse + merge (oficial > DefiLlama) → `begin_bridge_addresses_ingest` → `append_*` (chunks 500) → `commit_bridge_addresses_ingest`.

**Incluye:** gateways, routers, pools Stargate, spoke/hub Across, CCIP routers, Wormhole core/token_bridge, Axelar gateway — multichain (EVM + Solana/Aptos donde aplique).

**Disclaimer:** señal de exposición on-chain — no screening oficial.

Vault: [[12 - Workers/Bridge Addresses/Índice]]  
BD: [internal-bridge-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-bridge-addresses.md)  
ADR: [[2026-08-29 - Worker bridge addresses multi-fuente]]  
GHA (1er ingest): https://github.com/walpulse/workers/actions/runs/33137096800

**Prod (2026-08-28):** 945 filas · hash `4dcd0769…` · fuentes: defillama 487, stargate-api 210, wormhole 66, across 54, axelar 51, hop 43, ccip 34.

## Pendientes / diseño

| Tema | Notas |
|------|-------|
| Orquestador Origins | Consumir `internal.cex_addresses`, `internal.ofac_sdn_addresses`, `internal.mixer_addresses` y `internal.bridge_addresses` al calcular señales |
| `cex_quality` | Señal Walpulse; no viene de Spellbook |

---

*Actualizado 2026-08-29*
