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
| Schedule | `2 */6 * * *` UTC — arranca ventana continua |
| Continuo | Loop ~5h58m; **poll cada 60 s**; `timeout-minutes: 360` |
| Oneshot | `push` paths / `workflow_dispatch` (sin `continuous`) |
| Dispatch continuo | `continuous=true` → mismo loop 6 h |
| Skip | sin `pdf_cid`, ya `email_sent_at`, sin email de petición ni de cliente |

**Pipeline:** `list_analisis_requests_pending_email` (`notify_email` = coalesce) → plantilla i18n (`idioma`) → Resend → `set_analisis_request_email_sent`.

**Incluye:** link gateway Pinata al PDF + links JSON CIDs; disclaimer de señales.

**No incluye:** adjunto PDF; Básica; contacto web.

Secrets: `SUPABASE_*` + `RESEND_KEY` (+ opcional `EMAIL_FROM`; alias local `RESEND_API_KEY`).

## Operación continua (GHA)

GitHub Actions no permite cron más frecuente que 5 min ni un daemon 24/7. El patrón acordado:

1. Cada 6 h UTC (`:02`) arranca un job de hasta **360 min**.
2. Dentro del job: ejecutar el worker → `sleep 60` → repetir hasta ~5h58m.
3. Push / dispatch normal = **una** corrida (no quema la cuota de Actions).

Ventanas: **00:02 / 06:02 / 12:02 / 18:02 UTC**. Para cubrir un hueco tras deploy: Actions → *Run workflow* → `continuous=true`.

BD: [analisis-email.md](https://github.com/walpulse/database/blob/main/docs/analisis-email.md)  
ADR vault: `08 - Decisiones/2026-09-04 - Correo post-PDF via worker y Resend`
