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
| Fuente | Tornado Cash docs + L2BEAT Privacy `discovered.json` (8 protocolos) + Railgun deployments + Cyclone docs |
| Destino | `internal.mixer_addresses` |
| Trigger | Push `main`, cron diario 08:00 UTC, `workflow_dispatch` (+ `force`) |
| Skip | SHA-256 compuesto (Tornado + L2BEAT + Railgun + Cyclone [+ Typhoon seed]) == `mixer_addresses_sync.source_hash` |

**Pipeline:** fetch fuentes → parse pools/routers/entrypoints + `privacy_mechanism` + `catalog_tier` → `begin` → `append_*` → `commit`.

**Taxonomía:** `privacy_mechanism` (`zk_pool` / `stealth` / `fhe_wrapper` / `tee`) · `catalog_tier` (`canonical` / `fork`). Catalog-only.

**Incluye:** Tornado Classic L1/L2 + router + Nova; Privacy Pools, Railgun multi-chain (deployments), Umbra, Privacy Boost, Zama, STRK-20; **Cyclone** anonymity pools EVM (`fork`). Typhoon omitido v1 (seed vacío).

**Disclaimer:** señal de exposición on-chain — no screening oficial.

Vault: [[12 - Workers/Mixer Addresses/Índice]]  
BD: [internal-mixer-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-mixer-addresses.md)  
ADR: [[2026-08-28 - Worker mixer addresses Tornado L2BEAT]] · [[2026-08-29 - Taxonomía privacy_mechanism mixer addresses]] · [[2026-08-29 - Mixer Railgun multi-chain catalog_tier forks]]  
GHA (1er ingest): https://github.com/walpulse/workers/actions/runs/33136022223

**Prod:** 86 filas (canonical 76 · fork 10 cyclone); Railgun ETH/Arb/Polygon/BSC — [GHA 33232651871](https://github.com/walpulse/workers/actions/runs/33232651871).

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
| Fuente | **Goldsky** privado `walpulse-scout-curate/1.0.0` (gtcr-subgraph Gnosis); Graph/Envio solo `--source` opt-in |
| Destino | `internal.kleros_scout_addresses` |
| Trigger | Push `main`, cron diario 10:00 UTC, `workflow_dispatch` (+ `force`) |
| Skip | Fingerprint `(registry, itemID, resolutionTime)` == `kleros_scout_addresses_sync.source_hash` |

**Pipeline:** GraphQL paginado (3 TCR Scout canónicos) → parse CAIP/key0–key3 → `begin_kleros_scout_addresses_ingest` → `append_*` (chunks 500) → `commit_kleros_scout_addresses_ingest`.

**Registros:** Address Tags, Tokens (`0xeE15…`), Contract-Domain/CDN (Gnosis Curate). Sin ATQ.

**Disclaimer:** label de contraparte curada — no verificación oficial ni screening.

Vault: [[12 - Workers/Kleros Scout/Índice]]  
BD: [internal-kleros-scout-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-kleros-scout-addresses.md)  
ADR: [[2026-08-28 - Worker Kleros Scout address tags The Graph]]

**Prod (2026-08-30):** Goldsky propio — **16.591 filas** · hash `fcc002bbbf79…` · address_tag / token canónico / CDN. Reemplazó snapshot Envio (12.504).  
GHA: https://github.com/walpulse/workers/actions/runs/33287567173

**Nota previa (2026-08-28):** snapshot Envio 12.504 (Tokens TCR viejo) — obsoleto.

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
Docs: [spellbook-labels.md](./spellbook-labels.md)  
ADR: [[2026-08-28 - Worker Spellbook labels git static]]

**Prod (2026-08-28):** 9.363 filas · hash `57735ae7f7f5f33…` · por categoría: institution 8.120, dao 483, infrastructure 443, bridge 279, ofac_sanction 38.  
GHA (1er ingest): https://github.com/walpulse/workers/actions/runs/33142465039

### 7. `sourcify_verified` — Catálogo contratos verificados Sourcify (PAUSADO path crítico)

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/sourcify-verified.yml` (**solo `workflow_dispatch`** — cron/push off) |
| Código | `workers/sourcify_verified/` |
| Fuente | [export.sourcify.dev](https://export.sourcify.dev) Parquet v2 (`contract_deployments`, `verified_contracts`) |
| Destino | `internal.sourcify_verified_addresses` (+ puente `sourcify_deployments`, manifest `sourcify_export_files`) |
| Trigger | Solo `workflow_dispatch` (`force`, `table`) — warm/backfill opcional |
| Estado | **No crítico** desde 2026-09-03. Path de producto = Edge `sourcify-lookup` + cache on-demand (Estándar/Experta) |

**Pipeline (legado):** list GCS XML → comparar manifest → download 1 Parquet / vez → PyArrow stream → upserts → `record_sourcify_export_file`.

**Disclaimer:** señal de source verificado Sourcify — no auditoría ni screening oficial.

Vault: `12 - Workers/Sourcify Verified`  
BD: [internal-sourcify-verified.md](https://github.com/walpulse/database/blob/main/docs/internal-sourcify-verified.md) · [sourcify-lookup.md](https://github.com/walpulse/database/blob/main/docs/sourcify-lookup.md)  
ADR vigente: `2026-09-03 - Sourcify on-demand via Edge + cache`  
ADR histórico: `2026-08-29 - Worker Sourcify verified addresses Parquet export`

### 8. `token_taxonomy` — Taxonomía tokens CoinGecko + DefiLlama

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/token-taxonomy.yml` |
| Código | `workers/token_taxonomy/` |
| Fuente | CoinGecko Demo API (12 categorías CG + top-100 market cap) + DefiLlama stablecoins (API + `peggedassets-server` git) |
| Destino | `internal.token_taxonomy` |
| Trigger | Push `main`, cron diario **12:00 UTC**, `workflow_dispatch` (+ `force`) |
| Skip | SHA-256 fingerprint (CG + DefiLlama) == `token_taxonomy_sync.source_hash` |
| Presupuesto API | **~42 créditos/sync** CoinGecko (~1.260/mes cron diario) |

**Pipeline:** sparse-clone peggedassets-server → DL API fiat stables → hybrid DL (git addresses + CG expand gaps) → `/coins/list` + `/coins/markets` por categoría + bluechip → merge union CG ∪ DL → `begin_token_taxonomy_ingest` → `append_*` (chunks 500) → `commit_token_taxonomy_ingest`.

**Tags Walpulse:** `stable`, `meme`, `airdrop`, `bluechip`. Precedencia scoring (orquestador): stable → meme → airdrop → bluechip → other. DefiLlama aporta tag `stable` (fiat pegs, excl. `peggedVAR`); merge union, no replace.

**No incluye:** categoría `pepe` (404 CG); Solana/non-EVM v1; `/coins/{id}` por coin.

Vault: [[12 - Workers/Token Taxonomy/Índice]]  
BD: [internal-token-taxonomy.md](https://github.com/walpulse/database/blob/main/docs/internal-token-taxonomy.md)  
ADR: [[2026-08-28 - Worker token taxonomy CoinGecko]] · [[2026-08-28 - Token taxonomy v1.1 DefiLlama hybrid]]

**Prod v1 (2026-08-28):** 3.602 filas · hash `76ad6de7eac3f14b…` · por tag: meme 2.463, stable 883, bluechip 167, airdrop 103.  
**Prod v1.1 (2026-08-28):** 3.947 filas · hash `da374aac1d5f4aad…` · por tag: meme 2.463, stable **1.239**, bluechip 167, airdrop 103 (+356 stable vs v1).  
GHA v1: https://github.com/walpulse/workers/actions/runs/33200726658 · GHA v1.1: https://github.com/walpulse/workers/actions/runs/33202112607

### 9. `airdrop_contracts` — Claim / merkle distributors

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/airdrop-contracts.yml` |
| Código | `workers/airdrop_contracts/` |
| Fuente | `contracts.yaml` curado + factories Sablier (`CreateMerkle*` **incremental** vía `ALCHEMY_KEY`) + Spellbook metadata |
| Destino | `internal.airdrop_contracts` |
| Trigger | Push `main`, cron diario **10:00 UTC**, `workflow_dispatch` (+ `force`, `skip_factories`) |
| Skip | SHA-256 (`contracts` + `factories` + clones) == `airdrop_contracts_sync.source_hash` |

**Pipeline:** curated YAML → factories incremental (`airdrop_factory_scan` cursors + `ALCHEMY_KEY`) → merge clones BD ∪ nuevos → Spellbook enrichment → `eth_getCode` → ingest.

**Factories / Alchemy:**
- Primera vez (sin cursor): lookback `AIRDROP_FACTORY_BOOTSTRAP_BLOCKS` (default **5000**), no historia completa.
- `eth_getLogs` con chunk adaptativo (Alchemy **Free** = máx **10** bloques/query; PAYG = rangos amplios).
- `--force` = full desde `from_block` YAML — en Free es muy lento; preferí PAYG para backfill histórico.
- Habilitar chains en el app Alchemy (p. ej. **OP Mainnet**, Scroll, Linea).
- Curated con `empty_code` se **conservan** (distribuidores históricos selfdestruct/migrados); clones factory sí se rechazan si vacío.

**No incluye:** Galxe; CryptoRank; Dune API. 1inch sin factory → solo curated.

Vault: [[12 - Workers/Airdrop Contracts/Índice]]  
BD: [internal-airdrop-contracts.md](https://github.com/walpulse/database/blob/main/docs/internal-airdrop-contracts.md)

### 10. `protocol_addresses` — Catálogo contratos DeFi (factory/router/…)

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/protocol-addresses.yml` |
| Código | `workers/protocol_addresses/` |
| Fuente | P0 `data/official_seed.json` · P1 Spellbook VALUES · P2 DefiLlama adapters (gated) |
| Destino | `internal.protocol_addresses` |
| Trigger | Push `main`, cron diario **13:00 UTC**, `workflow_dispatch` (`force`, `layers`) |
| Skip | Fingerprint compuesto por capas == `protocol_addresses_sync.source_hash` |

**Pipeline:** load seed (± sparse-clone Spellbook/DefiLlama) → merge `official` > `spellbook` > `defillama` → `begin_*` → `append_*` (chunks 500) → `commit_*` (preserva `origin=discovered`).

**Incluye:** Uniswap, Aave, Compound, Lido, EigenLayer, Curve, 1inch, CoW, Seaport, Permit2, LI.FI/Socket (`kind=aggregator`).

**No incluye:** pools LP (lazy cache Origins vía `upsert_protocol_address_discovered`).

Vault: [[12 - Workers/Protocol Addresses/Índice]]  
BD: [internal-protocol-addresses.md](https://github.com/walpulse/database/blob/main/docs/internal-protocol-addresses.md)  
ADR: [[2026-08-28 - Worker protocol addresses capas P0 P1 P2]]

### 11. `analisis_pdf` — PDF del análisis Estándar / Experta

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/analisis-pdf.yml` |
| Código | `workers/analisis_pdf/` |
| Fuente | `walpulse.analisis_requests` (JSON `analisis-v1` ya packaged) |
| Destino | `pdf_cid` (Pinata / IPFS) |
| Trigger | Push paths, cron cada 10 min UTC, `workflow_dispatch` (`limit`) |
| Skip | Sin filas pendientes (`pdf_cid` null + candidatas) |

**Pipeline:** list pending → HTML/CSS Identidad Visual → WeasyPrint → Pinata pinFile → `set_analisis_request_pdf_cid`.

**Incluye:** solo `estandar` / `experta` con `succeeded` o `succeeded_with_warnings` y `analisis_cid`.

**No incluye:** correo; Básica; anclaje EAS del PDF.

Vault: [[12 - Workers/Analisis PDF/Índice]]  
BD: [analisis-pdf.md](https://github.com/walpulse/database/blob/main/docs/analisis-pdf.md)  
Docs: [analisis-pdf.md](./analisis-pdf.md)  
ADR: [[2026-09-03 - PDF analisis via worker y Pinata]]

## Pendientes / diseño

| Tema | Notas |
|------|-------|
| Orquestador Origins | Consumir `internal.*` + heurística factory→pool + UPSERT discovered |
| `cex_quality` | Señal Walpulse; no viene de Spellbook |
| Correo post-PDF | Fuera del ADR PDF; notificar cuando exista `pdf_cid` |

---

*Actualizado 2026-09-03 (analisis_pdf)*
