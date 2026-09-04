# analisis_pdf

Worker que genera el **PDF** del análisis Estándar / Experta, lo pinnea en Pinata y guarda `pdf_cid`.

Proceso **aparte** del pipeline de señales (`analisis-*-run` / `analisis-entregables`). No envía correo. No modifica el schema EAS.

Hero del PDF: `grade_label` + `synthesis.summary` según `idioma` (`es`|`en`|`pt`); sin `weights_version`.
Señales: todas las claves planas de `highlights`+`signals` con labels i18n; hops Origins + `counterparties_light` en Activity.

## Flujo

1. `list_analisis_requests_pending_pdf(limit)` — filas `estandar|experta`, `succeeded*`, con `analisis_cid`, sin `pdf_cid`
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

- Repo: [docs/analisis-pdf.md](../../docs/analisis-pdf.md) (si existe) · [docs/PROCESSES.md](../../docs/PROCESSES.md)
- BD: [analisis-pdf.md](https://github.com/walpulse/database/blob/main/docs/analisis-pdf.md)
- ADR: `2026-09-03 - PDF analisis via worker y Pinata`

<!-- reprocess -->

Idioma del PDF: columna `idioma` (es|en|pt).

<!-- retrigger page layout smoke -->


<!-- polish smoke retrigger -->


<!-- retrigger 2026-09-04 hop-groups -->


<!-- retrigger en pdf 2026-09-04 -->

