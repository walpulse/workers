# analisis_email

EnvÃ­a correo transaccional cuando `pdf_cid` ya estÃ¡ seteado (EstÃ¡ndar / Experta).

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/analisis-email.yml` |
| Destinatario | `analisis_requests.email` → fallback `clientes.email` |
| Provider | Resend |
| From | `Walpulse <hello@mail.walpulse.com>` (`EMAIL_FROM` override) |
| Dominio | `mail.walpulse.com` (verificado en Resend; DNS Spaceship) |
| Secret GHA | `RESEND_KEY` |
| PDF | link gateway Pinata (sin adjunto) |
| Idioma | `analisis_requests.idioma` (`es`\|`en`\|`pt`) |

## Pipeline

`list_analisis_requests_pending_email` â†’ plantilla i18n â†’ Resend â†’ `set_analisis_request_email_sent`.

## Local

```powershell
$env:SUPABASE_URL = "https://api.walpulse.com"
$env:SUPABASE_SERVICE_ROLE_KEY = "<service_role>"
$env:RESEND_KEY = "<resend>"
uv run python -m workers.analisis_email.job --limit 5
# ReenvÃ­o
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
