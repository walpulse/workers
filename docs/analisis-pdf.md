# analisis_pdf — PDF Estándar / Experta → Pinata

Worker aparte del pipeline de señales. Genera PDF determinístico desde `analisis-v1`, pinnea en Pinata, persiste `walpulse.analisis_requests.pdf_cid`.

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/analisis-pdf.yml` |
| Código | `workers/analisis_pdf/` |
| Destino | `pdf_cid` (CID IPFS) |
| Tiers | `estandar`, `experta` |
| Idioma | columna `idioma` (`es`\|`en`\|`pt`) — chrome UI, labels de señales y narrativas |
| Trigger | cron `*/10`, `workflow_dispatch` (`limit` / `force` / `request_ids`), push paths |
| Skip | filas con `pdf_cid` ya set / no candidatas |

**Pipeline:** `list_analisis_requests_pending_pdf` → WeasyPrint (Identidad Visual, i18n) → Pinata `pinFileToIPFS` → `set_analisis_request_pdf_cid`.

## Layout del PDF (4 páginas)

| Página | Contenido |
|--------|-----------|
| 1 | Header, síntesis (`grade_label` + `summary`), vista general de módulos, **Multichain** (señales + tabla chains / última tx) |
| 2 | **Portafolio** + **Compliance screen OFAC** |
| 3 | **Orígenes** — hops en ramas `Hop 1x → Hop 2x` (vínculo `via`) |
| 4 | **Actividad** (señales + contrapartes top), **Data Providers**, disclaimer, enlaces IPFS Pinata gateway |

**Footer running (todas las páginas):** izquierda — identificación (`request_id`), wallet, fecha; derecha — `N/N`, atribución Walpulse, disclaimer de señales (no decisorio).

**Data Providers:** lista estática (i18n) — Goldrush; Alchemy / EtherScan / BlockScout / Ankr; Zerion; Nsgood; Kleros; Sourcify; CoinGecko / DefiLlama / Spellbook y otros públicos.

## Formato de señales

- Ratios / `*_pct*` / HHI (escala 0–1) → porcentaje (`42%`).
- Valores monetarios (`*_usd*` excepto HHI, p. ej. `total_value_usd_credible`) → `$14.12`.
- Conteos (`*_positions`, `*_count`) → entero, nunca `%`.
- Origins hop 2: etiqueta **Wallet fondeada** + address completa.
- Peso relativo: % entre peers del mismo nivel/rama; fracciones diminutas → `<0.1%`.

## Orígenes — ramas

Cada hop 1 (ordenado por peso desc) abre una rama `a`, `b`, …; sus hop 2 hijos (`via` = address del padre) van debajo (`Hop 2a`, `Hop 2a.1`…). Activity lights siguen lista plana.

**No incluye:** correo; PDF para Básica; cambios EAS.

Secrets: `SUPABASE_*` + `PINATA_JWT` / `PINATA_API_KEY` / `PINATA_API_SECRET`.

BD: [analisis-pdf.md](https://github.com/walpulse/database/blob/main/docs/analisis-pdf.md)  
ADR: `2026-09-03 - PDF analisis via worker y Pinata` (actualización layout 2026-09-04)
