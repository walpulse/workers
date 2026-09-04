# analisis_email

Envía correo transaccional cuando `pdf_cid` ya está seteado (Estándar / Experta).

| Campo | Valor |
|-------|--------|
| Workflow | `.github/workflows/analisis-email.yml` |
| Destinatario | `walpulse.clientes.email` |
| Provider | Resend |
| From | `Walpulse <hello@walpulse.com>` (`EMAIL_FROM` override) |
| PDF | link gateway Pinata (sin adjunto) |

## Pipeline

`list_analisis_requests_pending_email` → plantilla i18n → Resend → `set_analisis_request_email_sent`.

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

Dominio `walpulse.com` debe estar verificado en Resend para `hello@walpulse.com`.

## Docs

- Repo: [docs/analisis-email.md](../../docs/analisis-email.md)
- BD: [analisis-email.md](https://github.com/walpulse/database/blob/main/docs/analisis-email.md)
