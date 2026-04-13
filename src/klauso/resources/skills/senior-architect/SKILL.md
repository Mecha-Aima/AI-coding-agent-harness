---
name: senior-architect
description: >-
  System design, ADRs, dependency and layering guidance for the coding-agent-harness
  codebase: core loop vs harness modules, tools, MCP, permissions, and tutorial s*.py
  scripts. Use when designing features, comparing patterns, drawing architecture
  diagrams, or planning refactors across core.py, harness/, and config/.
---

# Senior architect (this harness)

## System map (mental model)

```text
User / REPL
    → agent loop (stream + tools)
        → permissions (YAML)
        → dispatch (bash, read, write, … + MCP + skills)
        → optional: sessions, compaction, teams, workers
```

Key roots in **this repo**:

| Area | Typical files |
|------|----------------|
| Loop + tools merge | `core.py`, `harness/` |
| Config | `config/permissions.yaml`, `config/mcp_config.yaml` |
| Runnable tutorials | `s01_*.py` … `s21_*.py` (isolated demos) |
| Skills injected into model | `skills/*/SKILL.md` |

## When to produce an ADR

Use a short **ADR** (Context / Decision / Consequences) when choosing:

- New **tool** vs **skill** vs **MCP** capability.
- **Async** vs sync dispatch, or where to place **thread** boundaries.
- **Monolith harness** vs splitting packages (trade maintainability vs import graph).

## Patterns vs this codebase

- **Modular monolith** fits: keep orchestration in `harness/`, tool implementations colocated, avoid circular imports from `core.client` in low-level tests where possible.
- **Microservices**: usually **out of scope** unless the user explicitly runs distributed agents; prefer documenting boundaries in ADR first.

## Diagrams

Prefer **Mermaid** (`graph TD`, `sequenceDiagram`) in chat or markdown the user saves; keep diagrams in sync with actual module names (`harness/skills_meta.py`, not fictional paths).

## Dependency thinking

- Who imports **Anthropic client**? Keep heavy SDK imports out of cold paths if tests need to run without keys.
- MCP stdio servers: lifecycle and **cancel scopes** belong with the lifespan owner (see harness MCP runtime patterns).

## Anti-patterns for this repo

- Inventing **`scripts/architecture_diagram_generator.py`** unless it exists.
- Renaming **`SKILLS_DIR`** consumers without updating `core/settings.py` and docs.
