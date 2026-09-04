# analisis_email — correo post-PDF → Resend

Worker aparte de `analisis_pdf`. Cuando existe `pdf_cid`, notifica a `walpulse.clientes.email`.

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/analisis-email.yml` |
| Código | `workers/analisis_email/` |
| Destinatario | `clientes.email` |
| Provider | Resend |
| Trigger | cron `*/10`, `workflow_dispatch` (`limit` / `force` / `request_ids`), push paths |
| Skip | sin `pdf_cid`, ya `email_sent_at`, cliente sin email |

**Pipeline:** `list_analisis_requests_pending_email` → plantilla i18n (`idioma`) → Resend → `set_analisis_request_email_sent`.

**Incluye:** link gateway Pinata al PDF + links JSON CIDs; disclaimer de señales.

**No incluye:** adjunto PDF; email por request; Básica; contacto web.

Secrets: `SUPABASE_*` + `RESEND_KEY` (+ opcional `EMAIL_FROM`; alias local `RESEND_API_KEY`).

**From:** `Walpulse <hello@mail.walpulse.com>` — dominio de envío `mail.walpulse.com` (verificar en Resend).

BD: [analisis-email.md](https://github.com/walpulse/database/blob/main/docs/analisis-email.md)
