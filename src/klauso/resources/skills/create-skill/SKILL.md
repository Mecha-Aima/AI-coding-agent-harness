---
name: create-skill
description: >-
  Guides creation of new harness skills as markdown under skills/<name>/SKILL.md,
  YAML frontmatter, and optional reference files. Use when authoring or updating
  skills for this coding-agent-harness repo or when the user asks about skill
  structure, descriptions, or load_skill integration.
---

# Create skill (this harness)

## When to use

- User wants a **new** or **updated** skill for behavior loaded by `load_skill`.
- Questions about `SKILL.md` format, descriptions, or splitting long content.

## Where skills live in *this* repo

| Location | Role |
|----------|------|
| **`skills/<skill-name>/SKILL.md`** | Primary — discovered by `harness/skills_meta.py` (`SKILLS_DIR` = repo `skills/`) |
| **`skills/<skill-name>/reference.md`** (optional) | Deep detail; load only when needed |
| **`skills/<skill-name>/examples.md`** (optional) | Copy-paste patterns |

**Cursor-only paths** (`~/.cursor/skills/`, `.cursor/skills/`) apply to the Cursor editor agent, not this Python harness. Do not confuse the two when the user runs the harness REPL.

## Required shape

```markdown
---
name: my-skill-name
description: >-
  Third-person, WHAT + WHEN, under ~1024 chars. Include trigger phrases
  ("Use when …") so list_skills summaries are useful.
---

# Title

## When to use
...
```

Rules:

- **`name`**: lowercase, hyphens, max 64 chars; folder name should match `name` for clarity.
- **`description`**: third person ("Provides…", "Use when…"); not "I can…".
- **Body**: concise; link `reference.md` instead of pasting huge blocks.

## How the harness reads descriptions

`discover_skills()` parses **`description:`** inside the first `--- … ---` YAML block. Keep `description` on one line or use folded YAML `>-` with the value starting on the same line when possible.

## Authoring principles

1. **Short main file** — the model already knows generic Python; only add harness- or domain-specific rules.
2. **One level of links** — `SKILL.md` → `reference.md`; avoid deep chains.
3. **No fake scripts** — do not reference `python scripts/foo.py` unless that file exists in this repo.
4. **Unix paths** in examples: `skills/foo/SKILL.md`, not backslashes.

## Checklist before finishing

- [ ] Valid YAML `---` frontmatter with `name` + `description`
- [ ] Folder name matches `load_skill` name the user will type
- [ ] Triggers in `description` match when you want `list_skills` to surface it
- [ ] No time-sensitive claims ("before 2025…") without a legacy note
