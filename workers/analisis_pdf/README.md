# analisis_pdf

Worker que genera el **PDF** del análisis Estándar / Experta, lo pinnea en Pinata y guarda `pdf_cid`.

Proceso **aparte** del pipeline de señales (`analisis-*-run` / `analisis-entregables`). No envía correo. No modifica el schema EAS.

## Contenido del PDF

- **Idioma:** columna `idioma` (`es`|`en`|`pt`) — chrome, labels i18n y narrativas.
- **Hero:** `grade_label` + `synthesis.summary` (sin `weights_version`).
- **Custodia:** bloque raíz `custody_classification` (clase + % hosted/unhosted/unknown + confidence).
- **Señales:** `highlights` solo ordena (keys curadas primero); **valores** desde `signals` agregados (si chocan, gana `signals`). Ratios/HHI/`*_pct` como `%`; `*_usd*` (salvo HHI) con `$`; conteos como entero.
- **Multichain:** señales + tabla `main_chains` (nombre + última tx).
- **Orígenes:** señales planas (incl. CEX deposit inferred) + `origin_entity_clusters` (tabla % + top origins) + hops = **screening `funder_risk`** (ramas `Hop 1a → Hop 2a` por `via`; resumen OFAC/mixer/CEX/bridge; skips CEX con `cex_name`).
- **Activity:** señales (incl. `kleros_tagged_contract_pct`) + contrapartes (`counterparties_light` o fallback `top_counterparties`) con peso relativo + **Entrada/Salida** (`in_weight`/`out_weight` como % de la fila).
- **Data Providers:** lista estática de proveedores on-chain (Goldrush, Alchemy/Etherscan/BlockScout/Ankr, Zerion, Nsgood, Kleros, Sourcify, CoinGecko/DefiLlama/Spellbook).
- **Footer (todas las páginas):** id / wallet / fecha (izq.) · N/N + atribución Walpulse + disclaimer de señales (der.).
- **Layout:** pág. 1 síntesis/overview/custodia/Multichain · pág. 2 Portafolio + Compliance multi (OFAC/UN/EU/HMT) · pág. 3 Orígenes · pág. 4 Actividad + Data Providers + disclaimer + IPFS.
- **Compliance:** `compliance_screen` mode `multi` — resumen + tabla por lista + health condicional; `verdict`/`sanctioned` = semántica OFAC; limpio multi-lista vía `any_list_match`.

## Flujo

1. `list_analisis_requests_pending_pdf(limit)` — filas `estandar|experta`, `succeeded*`, con `analisis_cid`, sin `pdf_cid` (incluye `idioma`)
2. Render HTML/CSS institucional (Identidad Visual) → WeasyPrint → PDF
3. `pinFileToIPFS` (Pinata)
4. `set_analisis_request_pdf_cid(id, cid)` — idempotente

## GHA

| Modo | Cuándo |
|------|--------|
| Oneshot | `push` paths / `workflow_dispatch` |
| Continuo | schedule `0 */6 * * *` UTC · loop ~6 h · poll **60 s** · `timeout-minutes: 360` |
| Continuo manual | dispatch con `continuous=true` |

## Secrets GHA

| Secret | Uso |
|--------|-----|
| `SUPABASE_URL` | Proyecto Walpulse |
| `SUPABASE_SERVICE_ROLE_KEY` | RPCs |
| `PINATA_JWT` | Preferido |
| `PINATA_API_KEY` + `PINATA_API_SECRET` | Fallback si JWT falta/falla |

## Local

```powershell
cd C:\Walpulse\workers
pip install -r requirements.txt
# WeasyPrint en Windows puede requerir GTK; preferí validar en GHA/Ubuntu.
$env:SUPABASE_URL = "https://fxocgurmnirxvvkdzuyt.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "<service_role>"
python -m workers.analisis_pdf.job --dry-render --limit 1
# Full (necesita Pinata):
# python -m workers.analisis_pdf.job --limit 5
# Regenerar (sobrescribe pdf_cid):
# python -m workers.analisis_pdf.job --force --request-id <uuid>
```

## Tests

```powershell
pytest -q tests/test_analisis_pdf.py
```

## Docs

- Repo: [docs/analisis-pdf.md](../../docs/analisis-pdf.md) · [docs/PROCESSES.md](../../docs/PROCESSES.md)
- BD: [analisis-pdf.md](https://github.com/walpulse/database/blob/main/docs/analisis-pdf.md)
- Vault: `12 - Workers/Analisis PDF/`
- ADR: `2026-09-03 - PDF analisis via worker y Pinata`
- Hops: screening `funder_risk` (2026-09-08); skip reasons legibles en PDF

