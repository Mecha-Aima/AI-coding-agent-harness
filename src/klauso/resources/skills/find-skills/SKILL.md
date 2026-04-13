---
name: find-skills
description: >-
  Helps discover and install skills from the public ecosystem (skills.sh, npx skills)
  and contrasts them with this repo's built-in harness skills under skills/.
  Use when the user asks to find a skill, extend agent capabilities beyond this
  repository, or wants templates for testing, design, DevOps, or docs workflows.
---

# Find skills (ecosystem + this repo)

## When to use

- User asks how to do X and X might exist as an **installable** skill elsewhere.
- Phrases like "find a skill for…", "is there a skill for…", "npx skills", "skills.sh".
- User wants to **compare** external skills vs adding a local `skills/<name>/SKILL.md`.

## This repository first

Built-in harness skills live at **`skills/`** (see `core/settings.py` → `SKILLS_DIR`). They load via **`list_skills`** / **`load_skill`** in the agent loop. Prefer an existing repo skill when the task is harness-specific (tools, permissions, MCP, sessions).

## Public ecosystem (Cursor / agents)

The **Skills CLI** packages reusable workflows:

| Command | Purpose |
|--------|---------|
| `npx skills find [query]` | Search by keyword |
| `npx skills add <owner/repo@skill>` | Install from GitHub etc. |
| `npx skills check` / `npx skills update` | Maintenance |

Browse and verify popularity: [skills.sh](https://skills.sh/) (leaderboard for install counts).

## Quality bar before recommending

1. Prefer **1k+ installs**; be cautious below ~100.
2. Prefer known publishers (`vercel-labs`, `anthropics`, `microsoft`, …).
3. Glance at the **source repo** (stars, last commit) before endorsing.

## What to tell the user

Include: skill name, what it does, install count/source if known, install command, link on skills.sh.

Example:

```text
npx skills add vercel-labs/agent-skills@react-best-practices
```

Optional global non-interactive install: `npx skills add <pkg> -g -y` (only if the user wants it).

## If nothing fits

Offer to implement directly in this repo (Python harness, `harness/`, `core.py`, `s*.py` tutorials) or add a **local** skill under `skills/<name>/SKILL.md` (see `create-skill`).

## Category → example queries

| Area | Example `npx skills find …` |
|------|-----------------------------|
| Testing | `playwright e2e`, `jest` |
| Web | `nextjs`, `tailwind`, `react performance` |
| DevOps | `docker`, `github actions` |
| Docs | `changelog`, `openapi` |
