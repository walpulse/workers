# analisis_email

Envía correo transaccional cuando `pdf_cid` ya está seteado (Estándar / Experta). Si hay evaluations del Motor, espera `riesgo_cid` e incluye su link Pinata en el mismo correo.

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/analisis-email.yml` |
| Destinatario | `analisis_requests.email` → fallback `clientes.email` |
| Provider | Resend |
| From | `Walpulse <hello@mail.walpulse.com>` (`EMAIL_FROM` override) |
| Dominio | `mail.walpulse.com` (verificado en Resend; DNS Spaceship) |
| Secret GHA | `RESEND_KEY` |
| PDF | links gateway Pinata (análisis + Motor si aplica; sin adjunto) |
| Idioma | `analisis_requests.idioma` (`es`\|`en`\|`pt`) |
| Schedule | `2 */6 * * *` UTC → loop ~6 h / poll 60 s |
| Oneshot | push / dispatch; `continuous=true` para loop |

## Pipeline

`list_analisis_requests_pending_email` → plantilla i18n → Resend → `set_analisis_request_email_sent`.

Gate: `pdf_cid` set; si `evaluations` no vacío, también `riesgo_cid`.

## Local

```powershell
$env:SUPABASE_URL = "https://fxocgurmnirxvvkdzuyt.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "<service_role>"
$env:RESEND_KEY = "<resend>"
uv run python -m workers.analisis_email.job --limit 5
# Reenvío
uv run python -m workers.analisis_email.job --force --request-id <uuid>
```

## Secrets GHA

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `RESEND_KEY`

## Docs

- Repo: [docs/analisis-email.md](../../docs/analisis-email.md)
- BD: [analisis-email.md](https://github.com/walpulse/database/blob/main/docs/analisis-email.md)
- Vault: `12 - Workers/Analisis Email/`
- ADR: `2026-09-04 - Correo post-PDF via worker y Resend`
