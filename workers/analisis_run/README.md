# analisis_run

Orquestador GHA de análisis **Estándar / Experta**.

## Qué hace

1. Claim FIFO (`claim_analisis_requests_for_run`, stale 12 min)
2. Secuencia HTTP a Edges de módulo + ensamblado
3. Persist `analisis` / `evidencia` / …
4. `analisis-entregables`
5. Ante error: `failed` + mensaje (nunca zombie silencioso)

## Qué no hace

- Scoring / grades en Python
- PDF / email (otros workers)
- Análisis Básica sync

## Operación

| Trigger | Comportamiento |
|---------|----------------|
| `schedule` `0 */6` | Loop ~6 h / poll **45 s** |
| `workflow_dispatch` | Oneshot; `continuous=true` = mismo loop |
| `push` paths | Oneshot + tests |

```bash
pytest -q tests/test_analisis_run.py
python -m workers.analisis_run.job --limit 1
```

Env: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

Detalle: [docs/analisis-run.md](../../docs/analisis-run.md).
