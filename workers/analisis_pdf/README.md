# analisis_pdf

Worker que genera el **PDF** del análisis Estándar / Experta, lo pinnea en Pinata y guarda `pdf_cid`.

Proceso **aparte** del pipeline de señales (`analisis-*-run` / `analisis-entregables`). No envía correo. No modifica el schema EAS.

## Contenido del PDF

- **Idioma:** columna `idioma` (`es`|`en`|`pt`) — chrome, labels i18n y narrativas.
- **Hero:** `grade_label` + `synthesis.summary` (sin `weights_version`).
- **Señales:** claves planas de `highlights`+`signals`; ratios/HHI/`*_pct` como `%`; `*_usd*` (salvo HHI) con `$`; conteos como entero.
- **Multichain:** señales + tabla `main_chains` (nombre + última tx).
- **Orígenes:** ramas `Hop 1a → Hop 2a` enlazadas por `via` (“Wallet fondeada” + address completa).
- **Activity:** `counterparties_light` en lista plana con % relativo.
- **Data Providers:** lista estática de proveedores on-chain (Goldrush, Alchemy/Etherscan/BlockScout/Ankr, Zerion, Nsgood, Kleros, Sourcify, CoinGecko/DefiLlama/Spellbook).
- **Footer (todas las páginas):** id / wallet / fecha (izq.) · N/N + atribución Walpulse + disclaimer de señales (der.).
- **Layout:** pág. 1 síntesis/overview/Multichain · pág. 2 Portafolio + OFAC · pág. 3 Orígenes · pág. 4 Actividad + Data Providers + disclaimer + IPFS.

## Flujo

1. `list_analisis_requests_pending_pdf(limit)` — filas `estandar|experta`, `succeeded*`, con `analisis_cid`, sin `pdf_cid` (incluye `idioma`)
2. Render HTML/CSS institucional (Identidad Visual) → WeasyPrint → PDF
3. `pinFileToIPFS` (Pinata)
4. `set_analisis_request_pdf_cid(id, cid)` — idempotente

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
