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

### 7. `token_taxonomy` — Taxonomía tokens CoinGecko + DefiLlama

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

### 8. `airdrop_contracts` — Claim / merkle distributors

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/airdrop-contracts.yml` |
| Código | `workers/airdrop_contracts/` |
| Fuente | `contracts.yaml` curado + factories Sablier vía **Envio GraphQL** + Spellbook metadata |
| Destino | `internal.airdrop_contracts` |
| Trigger | Push path-filtered, cron **semanal** lun 10:00 UTC, `workflow_dispatch` (`force`, `skip_factories`) |
| Skip | SHA-256 (`contracts` + `factories` + clones) == `airdrop_contracts_sync.source_hash` |

**Pipeline:** curated YAML → Envio `Campaign` (allowlist `factories.yaml`) → merge → Spellbook enrichment → ingest (sin Alchemy `eth_getLogs`).

**Factories / Envio (v1.1):**
- Endpoint: `https://indexer.hyperindex.xyz/508d217/v1/graphql` (override `SABLIER_ENVIO_URL`).
- Paginación `Campaign` filtrada por `factory.address`; map `chainId` → slug Walpulse.
- Sin `ALCHEMY_KEY`; block cursors `airdrop_factory_scan` legacy/unused.
- Si Envio falla: fallback a clones ya en BD; curated siempre se mantiene.

**No incluye:** Galxe; CryptoRank; Dune API. 1inch sin factory → solo curated.

Vault: [[12 - Workers/Airdrop Contracts/Índice]]  
BD: [internal-airdrop-contracts.md](https://github.com/walpulse/database/blob/main/docs/internal-airdrop-contracts.md)

### 9. `protocol_addresses` — Catálogo contratos DeFi (factory/router/…)

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

### 10. `analisis_pdf` — PDF del análisis + Motor de Riesgos

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/analisis-pdf.yml` |
| Código | `workers/analisis_pdf/` |
| Fuente | `walpulse.analisis_requests` (JSON `analisis-v1` ya packaged) |
| Destino | `pdf_cid` (análisis) + `riesgo_cid` (Motor, si hay `evaluations`) |
| Trigger | Push/dispatch = 1 corrida; schedule `0 */6 * * *` UTC = loop ~6 h / poll 60 s |
| Skip | Sin filas pendientes (`pdf_cid` / `riesgo_cid` null + candidatas) |
| Idioma | `analisis_requests.idioma` (`es`\|`en`\|`pt`) — ambos PDFs |

**Pipeline análisis:** list pending → HTML/CSS Identidad Visual → WeasyPrint → Pinata pinFile → `set_analisis_request_pdf_cid`.

**Pipeline Motor:** `list_analisis_requests_pending_riesgo_pdf` → `template_riesgo.html` → Pinata (`analisis-riesgo-{id}.pdf`) → `set_analisis_request_riesgo_cid` (solo si `evaluations` no vacío).

**Incluye:** solo `estandar` / `experta` con `succeeded` o `succeeded_with_warnings` y `analisis_cid`. Layout análisis: síntesis/overview/**custodia**/Multichain+chains (pág. 1), Portafolio+**Compliance multi** (OFAC/UN/EU/HMT + `any_list_match`) (pág. 2), Orígenes (señales CEX inferred + `origin_entity_clusters` + hops `funder_risk`) (pág. 3), Actividad (incl. `kleros_tagged_contract_pct`)+Data Providers+disclaimer+IPFS (pág. 4); footer running en todas las páginas. PDF Motor: flujo continuo (identidad label/valor por matriz + reglas aplicadas/sin aplicar).

**No incluye:** correo; Básica; anclaje EAS del PDF.

Vault: [[12 - Workers/Analisis PDF/Índice]]  
BD: [analisis-pdf.md](https://github.com/walpulse/database/blob/main/docs/analisis-pdf.md)  
Docs: [analisis-pdf.md](./analisis-pdf.md)  
ADR: [[2026-09-03 - PDF analisis via worker y Pinata]]

### 11. `analisis_email` — Correo transaccional post-PDF

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/analisis-email.yml` |
| Código | `workers/analisis_email/` |
| Fuente | `analisis_requests` con `pdf_cid` (+ `riesgo_cid` si hay evaluations); destinatario = `email` de la petición o `clientes.email` |
| Destino | Resend → inbox; marca `email_sent_at` |
| Trigger | Push/dispatch = 1 corrida; schedule `2 */6 * * *` UTC = loop ~6 h / poll 60 s |
| Skip | Sin candidatas (`email_sent_at` set / sin email petición ni cliente / sin `pdf_cid` / esperando `riesgo_cid`) |
| Idioma | `analisis_requests.idioma` (`es`\|`en`\|`pt`) |

**Pipeline:** `list_analisis_requests_pending_email` → plantilla i18n → Resend → `set_analisis_request_email_sent`.

**Incluye:** link gateway Pinata al PDF de análisis + link al PDF del Motor (`riesgo_cid`) cuando aplica + CIDs JSON; disclaimer de señales.

**No incluye:** adjunto PDF; Básica; contacto web.

Vault: [[12 - Workers/Analisis Email/Índice]]  
BD: [analisis-email.md](https://github.com/walpulse/database/blob/main/docs/analisis-email.md)  
Docs: [analisis-email.md](./analisis-email.md)  
ADR: [[2026-09-04 - Correo post-PDF via worker y Resend]]

**Prod (2026-09-04):** dominio `mail.walpulse.com` verificado en Resend; From `hello@mail.walpulse.com`; smoke 7/7 + reenvío EN OK.  
GHA: https://github.com/walpulse/workers/actions/workflows/analisis-email.yml

### 12. `analisis_run` — Orquestación Estándar / Experta

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/analisis-run.yml` |
| Código | `workers/analisis_run/` |
| Fuente | `walpulse.analisis_requests` (`accepted` / stale `running`) |
| Destino | `analisis` / `evidencia` / entregables (vía Edges) |
| Trigger | Push paths / `workflow_dispatch` oneshot; schedule `0 */6 * * *` UTC = loop ~6 h / poll 45 s |
| Skip | Sin filas claimables |
| Claim | `claim_analisis_requests_for_run(≤5, 12)` |
| Paralelismo | `ThreadPoolExecutor` max **5**; client Supabase por hilo |
| Stages | `analisis_run_stages` + `run_progress` |

**Pipeline:** claim → HTTP módulos + empty/synthesize/custody (con stages) → persist → `analisis-entregables` → **skip riesgo** si el cliente no tiene matrices activas (`set_analisis_request_riesgo` con `sin_matrices_activas`); si hay matrices, deja `riesgo_evaluado_at` null para `analisis_riesgo`.

**Incluye:** Estándar + Experta. Hops = `funder_risk` (top 2/5, 1 chain; hop-2 Experta solo si hop-1 normal). Lights Activity. Retry 504 hijas. Pool ≤5. Compliance capa A = `compliance-screen` `mode=multi` (OFAC/UN/EU/HMT).

**No incluye:** Básica sync; PDF/email; scoring en Python; resume mid-flight; evaluación de matrices (salvo skip sin matrices).

Vault: [[12 - Workers/Analisis Run/Índice]]  
Docs: [analisis-run.md](./analisis-run.md)  
ADR: [[2026-09-07 - Worker analisis_run orquestacion Estandar Experta]] · [[2026-09-09 - Compliance screen-multi Estándar Experta]]

### 13. `analisis_riesgo` — Evaluador Motor de Riesgos

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/analisis-riesgo.yml` |
| Código | `workers/analisis_riesgo/` |
| Fuente | `analisis_requests` con `analisis` y `riesgo_evaluado_at IS NULL` |
| Destino | `riesgo` jsonb (`riesgo-evaluacion-v1`) + `riesgo_evaluado_at` |
| Trigger | Push/dispatch oneshot; schedule `1 */6 * * *` UTC = loop ~6 h / poll 45 s |
| Skip | Sin filas pendientes; o ya evaluado |
| Matrices | Sandbox del cliente (0..1) + todas las prod activas |

**Pipeline:** `list_analisis_requests_pending_riesgo` → `get_cliente_riesgo_matrices_activas` → evaluar reglas (`json_path` + operadores) → `set_analisis_request_riesgo`.

**Incluye:** Estándar/Experta; agregación `aggregate`/`root`/`per_chain`/`hop` (match si alguna cadena/hop cumple); trazabilidad por regla.

**No incluye:** render PDF (lo hace `analisis_pdf` → `riesgo_cid`); Básica.

Vault: [[12 - Workers/Analisis Riesgo/Índice]]  
Docs: [analisis-riesgo.md](./analisis-riesgo.md)  
BD: [analisis-riesgo.md](https://github.com/walpulse/database/blob/main/docs/analisis-riesgo.md)

## Pendientes / diseño

| Tema | Notas |
|------|-------|
| Orquestador Origins | Consumir `internal.*` + heurística factory→pool + UPSERT discovered |
| `cex_quality` | Señal Walpulse; no viene de Spellbook |

---

*Actualizado 2026-09-18 (email linkea riesgo_cid)*
