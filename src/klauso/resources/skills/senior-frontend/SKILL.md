---
name: senior-frontend
description: >-
  React, Next.js, TypeScript, Tailwind, accessibility, and component patterns for
  when this repo or the user's task includes a web UI, docs site, or harness
  dashboard. Use when the user mentions frontend, Next.js, React, CSS, a11y,
  bundle size, or client vs server components—even if the current tree is mostly Python.
---

# Senior frontend (for harness + adjacent UI work)

## Repo context

**coding-agent-harness** is primarily a **Python** agent harness (`core.py`, `harness/`, `s*.py`). There is no in-tree Next/React app by default. Apply this skill when:

- The user adds a **small UI** (e.g. status page, demo client) next to the harness.
- They ask **general** frontend questions while iterating on tooling.
- They embed a **web-based** agent or MCP playground.

## Defaults (when you do build UI)

- **Next.js App Router**: default to Server Components; add `'use client'` only for state, effects, events, browser APIs.
- **Data**: parallel `fetch` / server loaders where possible; use `Suspense` for slow regions.
- **Images**: `next/image` with explicit `width`/`height` or `fill` + `sizes`.
- **Styling**: Tailwind + `cn()`-style class merging for variants.
- **A11y**: semantic elements, `aria-*`, visible focus, keyboard paths for dialogs.

## Patterns (reference-level)

**Compound components** — share state via context for tabs, steppers, etc.

**Hooks** — extract `useDebounce`, `useLocalStorage`, media queries.

**Testing** — React Testing Library + userEvent; assert roles and accessible names, not only CSS selectors.

## Bundle hygiene

- Prefer **light** deps: `date-fns` / `dayjs` over `moment`; tree-shake `lodash-es` or use native utilities.
- Call out **large** imports (`@mui/*`, full icon packs) and suggest scoped imports or alternatives.

## What not to do here

- Do not assume repo scripts like `python scripts/frontend_scaffolder.py` exist unless the user added them.
- For harness-only work, defer to **`agent-builder`** and **`code-review`** skills.
