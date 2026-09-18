# Analisis Riesgo

Evalúa matrices activas del Motor de Riesgos (sandbox + producción) sobre el JSON `analisis-v1` y persiste `riesgo` / `riesgo_evaluado_at`.

## Pipeline

`analisis_run` → **`analisis_riesgo`** (si hay matrices) → `analisis_pdf` → `analisis_email`

Sin matrices: `analisis_run` escribe skip (`sin_matrices_activas`) y el PDF no espera este worker.

## Run local

```powershell
$env:SUPABASE_URL = "https://api.walpulse.com"
$env:SUPABASE_SERVICE_ROLE_KEY = "<service_role>"
python -m workers.analisis_riesgo.job --limit 5
```

Flags: `--request-id <uuid>` (repetible), `--force`.

## Tests

```powershell
pytest -q tests/test_analisis_riesgo.py
```
