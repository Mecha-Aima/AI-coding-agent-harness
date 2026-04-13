---
name: senior-backend
description: >-
  Python backend patterns for the harness: asyncio, subprocess safety, Anthropic
  Messages API usage, permissions, sessions, and MCP integration. Use when
  designing or reviewing API-facing code, tool dispatch, file I/O, or security
  in core.py and harness/.
---

# Senior backend (harness-focused)

## Stack assumptions

- **Language**: Python 3.11+.
- **LLM**: Anthropic Messages API (`tool_use` / `tool_result`), streaming where implemented.
- **Concurrency**: `asyncio` + `run_in_executor` for blocking SDK / subprocess work.
- **Config**: env + `config/*.yaml`; never commit secrets.

## Tool dispatch rules

- **Permissions first**: match policy strings against the **actual** command/path the tool will run (see `permissions.yaml` and harness permission helpers).
- **Idempotent reads**; **writes** should be reversible or clearly logged (snapshots where the harness provides them).
- **Subprocess**: fixed argv where possible; avoid `shell=True` unless necessary and permission-gated.

## API / protocol shape

- **MCP**: treat tool names and schemas as part of your public contract; handle **missing** servers gracefully.
- **Errors**: surface `stderr` / API error text to the model as **tool_result** strings, not silent pass.

## Security checklist

- YAML **always_deny** / **ask_user** tiers for destructive shell.
- No blind `eval` / `pickle` on untrusted paths.
- Validate paths stay under intended cwd when implementing new file tools.

## Performance

- Batch independent tool calls when the loop supports **parallel** execution.
- Avoid blocking the event loop: file IO and sync clients go to **threads** or async APIs.

## Testing

- Use **`pytest`** under `tests/` when present; mock Anthropic for unit tests.
- Prefer testing **pure** helpers without live network.

## Repo anchors

- **`core.py`**: historical single-file loop + tools (reference + production path depending on entrypoint).
- **`harness/`**: modular orchestration (events, MCP, skills meta, etc.) when present in tree.

Do **not** reference non-existent `python scripts/api_scaffolder.py` style tools unless the user adds them.
