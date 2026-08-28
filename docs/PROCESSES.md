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

### 5. `kleros_scout_addresses` — Catálogo Kleros Scout address tags

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/kleros-scout-addresses.yml` |
| Código | `workers/kleros_scout_addresses/` |
| Fuente | The Graph `legacy-curate-gnosis` (primario) + **Envio fallback** (operativo ago 2026) |
| Destino | `internal.kleros_scout_addresses` |
| Trigger | Push `main`, cron diario 10:00 UTC, `workflow_dispatch` (+ `force`) |
| Skip | Fingerprint `(registry, itemID, resolutionTime)` == `kleros_scout_addresses_sync.source_hash` |

**Pipeline:** GraphQL paginado (3 TCR Scout) → parse CAIP/key0–key3 → `begin_kleros_scout_addresses_ingest` → `append_*` (chunks 500) → `commit_kleros_scout_addresses_ingest`.

**Registros:** Address Tags, Tokens, Contract-Domain (Gnosis Curate). Sin ATQ.

**Disclaimer:** label de contraparte curada — no verificación oficial ni screening.

Vault: [[12 - Workers/Kleros Scout/Índice]]  
BD: [internal-kleros-scout-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-kleros-scout-addresses.md)  
ADR: [[2026-08-28 - Worker Kleros Scout address tags The Graph]]

**Prod (2026-08-28):** 12.504 filas · hash `74a0fc220c7f…` · fuente efectiva **Envio** (The Graph `legacy-curate-gnosis` NOT INDEXED — `no allocations`) · por registry: address_tag 8.024, contract_domain 3.228, token 1.252.  
GHA (1er ingest): https://github.com/walpulse/workers/actions/runs/33140546446

### 6. `spellbook_labels` — Catálogo labels estáticos Spellbook

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/spellbook-labels.yml` |
| Código | `workers/spellbook_labels/` |
| Fuente | Spellbook git: `labels/addresses` VALUES + `cex/addresses` mapeado |
| Destino | `internal.spellbook_labels` |
| Trigger | Push `main`, cron diario 11:00 UTC, `workflow_dispatch` (+ `force`) |
| Skip | SHA-256(`labels_commit:cex_commit`) == `spellbook_labels_sync.source_hash` |

**Pipeline:** sparse-clone (2 paths) → parse VALUES + CEX→labels → `begin_spellbook_labels_ingest` → `append_*` (chunks 500) → `commit_spellbook_labels_ingest`.

**Incluye:** stablecoins, bridges static, institution/CEX, OFAC static en labels, etc. (~9k filas).

**No incluye:** labels `source='query'` de Dune (`labels.addresses` completo). Sin Dune API.

Vault: [[12 - Workers/Spellbook Labels/Índice]]  
BD: [internal-spellbook-labels.md](https://github.com/walpulse/database/blob/main/docs/internal-spellbook-labels.md)  
ADR: [[2026-08-28 - Worker Spellbook labels git static]]

**Prod (2026-08-28):** 9.363 filas · hash `57735ae7f7f5f33…` · por categoría: institution 8.120, dao 483, infrastructure 443, bridge 279, ofac_sanction 38.  
GHA (1er ingest): https://github.com/walpulse/workers/actions/runs/33142465039

## Pendientes / diseño

| Tema | Notas |
|------|-------|
| Orquestador Origins | Consumir `internal.cex_addresses`, `internal.ofac_sdn_addresses`, `internal.mixer_addresses`, `internal.bridge_addresses`, `internal.kleros_scout_addresses` y `internal.spellbook_labels` al calcular señales |
| `cex_quality` | Señal Walpulse; no viene de Spellbook |

---

*Actualizado 2026-08-29 (spellbook_labels)*
