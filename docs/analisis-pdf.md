# analisis_pdf — PDF Estándar / Experta → Pinata

Worker aparte del pipeline de señales. Genera PDF determinístico desde `analisis-v1`, pinnea en Pinata, persiste `walpulse.analisis_requests.pdf_cid`. Si el envelope `riesgo` tiene `evaluations` no vacío, genera un **segundo PDF** del Motor de Riesgos y persiste `riesgo_cid`.

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/analisis-pdf.yml` |
| Código | `workers/analisis_pdf/` |
| Destino | `pdf_cid` (análisis) · `riesgo_cid` (Motor, opcional) |
| Tiers | `estandar`, `experta` |
| Idioma | columna `idioma` (`es`\|`en`\|`pt`) — chrome UI de ambos PDFs |
| Trigger | push/dispatch oneshot; schedule loop ~6 h / poll 60 s (`0 */6 * * *` UTC) |
| Continuo | Loop ~5h58m; **poll cada 60 s**; `timeout-minutes: 360` |
| Oneshot | `push` paths / `workflow_dispatch` (sin `continuous`) |
| Dispatch continuo | `continuous=true` → mismo loop 6 h |
| Skip análisis | filas con `pdf_cid` ya set / no candidatas |
| Skip Motor | `evaluations` vacío / `skipped_reason` / `riesgo_cid` ya set |

**Pipeline análisis:** `list_analisis_requests_pending_pdf` → WeasyPrint → Pinata → `set_analisis_request_pdf_cid`.

**Pipeline Motor:** `list_analisis_requests_pending_riesgo_pdf` → WeasyPrint (`template_riesgo.html`) → Pinata (`analisis-riesgo-{id}.pdf`) → `set_analisis_request_riesgo_cid`.

Flags ops: `--analisis-only` · `--riesgo-only` · `--force` (regenera CID según cola).

## Operación continua (GHA)

Mismo patrón que `analisis_email`: schedule cada 6 h UTC (`0 */6`) arranca un job que hace poll cada **60 s** hasta ~6 h (`timeout-minutes: 360`). Push/dispatch sin `continuous` = oneshot.

Ventanas: **00:00 / 06:00 / 12:00 / 18:00 UTC** (email arranca 2 min después).

## Layout del PDF de análisis (4 páginas)

| Página | Contenido |
|--------|-----------|
| 1 | Header, síntesis (`grade_label` + `summary`), vista general de módulos, **Clasificación de custodia** (`custody_classification`), **Multichain** (señales + tabla chains / última tx) |
| 2 | **Portafolio** + **Compliance screen** (multi: OFAC / UN / EU / HMT) |
| 3 | **Orígenes** — señales planas (incl. `cex_deposit_inferred_pct` / `cex_curated_pct`), **`origin_entity_clusters`** (tabla % + top origins), hops = **screening `funder_risk`** en ramas `Hop 1x → Hop 2x` (vínculo `via`; chips OFAC/mixer/CEX/bridge; skips CEX) |
| 4 | **Actividad** (señales incl. `kleros_tagged_contract_pct` + contrapartes: lights o `top_counterparties` con peso relativo + **Entrada/Salida**), **Data Providers**, disclaimer, enlaces IPFS Pinata gateway |

## Layout del PDF Motor de Riesgos

| Sección | Contenido |
|---------|-----------|
| Cabecera | Mismo look & feel; título Motor de Riesgos; wallet; `evaluated_at` |
| Resumen | Cards por evaluación (sandbox / producción): nombre matriz, versión, puntaje / presupuesto |
| Detalle | Una sección (page-break) por matriz: meta + tabla reglas matched + opcional no-matched |
| Cierre | Disclaimer de señales (no compliance) |

Chrome i18n `es`/`en`/`pt`; nombres de matriz/regla salen del JSON del cliente.

**Valores de señales:** `highlights` solo ordena (keys curadas primero); los **valores** salen de `signals` agregados. Si ambos definen la misma key, gana `signals`.

**Footer running (todas las páginas):** izquierda — identificación (`request_id`), wallet, fecha; derecha — `N/N`, atribución Walpulse, disclaimer de señales (no decisorio).

**Data Providers:** lista estática (i18n) — Goldrush; Alchemy / EtherScan / BlockScout / Ankr; Zerion; Nsgood; Kleros; Sourcify; CoinGecko / DefiLlama / Spellbook y otros públicos.

**Custodia:** bloque raíz (no Portfolio); clase + `p_hosted` / `p_unhosted` / `p_unknown` (0–100) + confidence; disclaimer de señal on-chain.

**Compliance (pág. 2):** `analisis.compliance_screen` en modo `multi` (Estándar/Experta). Resumen: verdict, sanctioned (semántica OFAC), `any_list_match`, firma, snapshot SDN. Tabla por lista OFAC/UN/EU/HMT (`matched` + version). `list_health` solo si feed unavailable o con `note`. Nota i18n: `verdict=clean` ≠ limpio en las cuatro listas. Fallback OFAC-only si no hay `lists` / `mode!=multi`.

**Clusters Origins:** buckets canónicos (exchange_vasp, exchange_deposit_inferred, …); copy *etiquetado* (no “regulado”); ceros omitidos.

## Formato de señales

- Ratios / `*_pct*` / HHI (escala 0–1) → porcentaje (`42%`).
- Valores monetarios (`*_usd*` excepto HHI, p. ej. `total_value_usd_credible`) → `$14.12`.
- Conteos (`*_positions`, `*_count`) → entero, nunca `%`.
- Origins hop 2: etiqueta **Wallet fondeada** + address completa.
- Hops Origins: screening `funder_risk` (no narrativa Origins completa); resumen generado desde señales OFAC/mixer/CEX/bridge + categoría; skip CEX → «Wallet excluida (…): {cex_name}».
- Peso relativo: % entre peers del mismo nivel/rama; fracciones diminutas → `<0.1%`.
- Activity contrapartes: `in_weight` / `out_weight` → **Entrada** / **Salida** como % del peso de esa fila (`in+out`); omitido si el JSON no trae esos campos.

## Orígenes — ramas

Cada hop 1 (ordenado por peso desc) abre una rama `a`, `b`, …; sus hop 2 hijos (`via` = address del padre) van debajo (`Hop 2a`, `Hop 2a.1`…). Activity lights siguen lista plana.

**No incluye:** correo (worker `analisis_email`); link de `riesgo_cid` en el mail (v1); PDF para Básica; cambios EAS.

Secrets: `SUPABASE_*` + `PINATA_JWT` / `PINATA_API_KEY` / `PINATA_API_SECRET`.

BD: [analisis-pdf.md](https://github.com/walpulse/database/blob/main/docs/analisis-pdf.md)  
ADR: `2026-09-03 - PDF analisis via worker y Pinata` · follow-up Motor PDF 2026-09-18
