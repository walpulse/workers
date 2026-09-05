# analisis_email — correo post-PDF → Resend

Worker aparte de `analisis_pdf`. Cuando existe `pdf_cid`, notifica por correo.

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/analisis-email.yml` |
| Código | `workers/analisis_email/` |
| Destinatario | `analisis_requests.email` si viene; si no, `clientes.email` |
| Provider | Resend |
| From | `Walpulse <hello@mail.walpulse.com>` |
| Dominio envío | `mail.walpulse.com` (verificado Resend) |
| Trigger | cron `*/5`, `workflow_dispatch` (`limit` / `force` / `request_ids`), push paths |
| Skip | sin `pdf_cid`, ya `email_sent_at`, sin email de petición ni de cliente |

**Pipeline:** `list_analisis_requests_pending_email` (`notify_email` = coalesce) → plantilla i18n (`idioma`) → Resend → `set_analisis_request_email_sent`.

**Incluye:** link gateway Pinata al PDF + links JSON CIDs; disclaimer de señales.

**No incluye:** adjunto PDF; Básica; contacto web.

Secrets: `SUPABASE_*` + `RESEND_KEY` (+ opcional `EMAIL_FROM`; alias local `RESEND_API_KEY`).

BD: [analisis-email.md](https://github.com/walpulse/database/blob/main/docs/analisis-email.md)  
ADR vault: `08 - Decisiones/2026-09-04 - Correo post-PDF via worker y Resend`
