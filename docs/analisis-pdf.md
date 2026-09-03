# analisis_pdf — PDF Estándar / Experta → Pinata

Worker aparte del pipeline de señales. Genera PDF determinístico desde `analisis-v1`, pinnea en Pinata, persiste `walpulse.analisis_requests.pdf_cid`.

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/analisis-pdf.yml` |
| Código | `workers/analisis_pdf/` |
| Destino | `pdf_cid` (CID IPFS) |
| Tiers | `estandar`, `experta` |
| Trigger | cron `*/10`, `workflow_dispatch`, push paths |
| Skip | filas con `pdf_cid` ya set / no candidatas |

**Pipeline:** `list_analisis_requests_pending_pdf` → WeasyPrint (Identidad Visual) → Pinata `pinFileToIPFS` → `set_analisis_request_pdf_cid`.

**No incluye:** correo; PDF para Básica; cambios EAS.

Secrets: `SUPABASE_*` + `PINATA_JWT` / `PINATA_API_KEY` / `PINATA_API_SECRET`.

BD: [analisis-pdf.md](https://github.com/walpulse/database/blob/main/docs/analisis-pdf.md)  
ADR: `2026-09-03 - PDF analisis via worker y Pinata`
