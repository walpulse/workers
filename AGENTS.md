# AGENTS.md — walpulse/workers

Punto de entrada para agentes que trabajan en **workers batch** de Walpulse (Python 3.12 / GitHub Actions).

**Bóveda:** [[12 - Workers/00 - Índice|12 - Workers]] · **BD:** repo `walpulse/database` + skill `walpulse-base-datos` · **Skill Cursor:** `walpulse-workers`

## Repos

| Repo | Rol |
|------|-----|
| [walpulse/workers](https://github.com/walpulse/workers) | Jobs Python + workflows GHA |
| [walpulse/database](https://github.com/walpulse/database) | Schema, migraciones, RPCs de ingest |

Supabase Walpulse: `fxocgurmnirxvvkdzuyt` — MCP `supabase-walpulse`. **No** usar GSA.

## Orden de lectura

1. Este `AGENTS.md`
2. [docs/PROCESSES.md](docs/PROCESSES.md)
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
4. [docs/SUPABASE.md](docs/SUPABASE.md)
5. Worker concreto: `workers/<name>/README.md`, `job.py`, `parse.py` (si aplica)
6. `.github/workflows/<name>.yml`
7. Bóveda: `12 - Workers/<Nombre worker>/`

## Workers live

| Carpeta | Workflow | Vault |
|---------|----------|-------|
| `cex_addresses` | `cex-addresses.yml` | [[12 - Workers/CEX Addresses/Índice]] |
| `ofac_sdn` | `ofac-sdn.yml` | [[12 - Workers/OFAC SDN/Índice]] |
| `mixer_addresses` | `mixer-addresses.yml` | [[12 - Workers/Mixer Addresses/Índice]] |
| `bridge_addresses` | `bridge-addresses.yml` | [[12 - Workers/Bridge Addresses/Índice]] |
| `kleros_scout_addresses` | `kleros-scout-addresses.yml` | [[12 - Workers/Kleros Scout/Índice]] |
| `spellbook_labels` | `spellbook-labels.yml` | [[12 - Workers/Spellbook Labels/Índice]] |
| `token_taxonomy` | `token-taxonomy.yml` | [[12 - Workers/Token Taxonomy/Índice]] |
| `airdrop_contracts` | `airdrop-contracts.yml` | [[12 - Workers/Airdrop Contracts/Índice]] |
| `protocol_addresses` | `protocol-addresses.yml` | [[12 - Workers/Protocol Addresses/Índice]] |
| `analisis_pdf` | `analisis-pdf.yml` | [[12 - Workers/Analisis PDF/Índice]] |
| `analisis_email` | `analisis-email.yml` | [[12 - Workers/Analisis Email/Índice]] |

## Reglas

1. **Schema primero** en `walpulse/database` si hay tablas/RPCs nuevos; aplicar migración antes de depender del worker.
2. Workers escriben `internal` vía RPC `SECURITY DEFINER` + `service_role` — no exponer schema en PostgREST.
3. **No secrets** en vault ni en git.
4. Documentar cada worker nuevo en bóveda `12 - Workers/<Nombre>/` (mismo set de notas que [[12 - Workers/Plantilla worker]]).
5. ADR en `08 - Decisiones` si es decisión de arquitectura; novedad en `11` solo si es comunicable.
6. Commits solo si el usuario lo pide.

## Nuevo worker (checklist)

- [ ] Migración + RPCs en `database` (si persiste)
- [ ] `workers/<name>/` + tests
- [ ] Workflow GHA + secrets documentados
- [ ] `docs/PROCESSES.md` + fila en este archivo
- [ ] Carpeta en bóveda `12 - Workers/`
- [ ] ADR si aplica

---

*Actualizado 2026-09-04 (analisis_email live — mail.walpulse.com)*
