# Configuration

YAML files in this directory are loaded at runtime from `core.settings.CONFIG_DIR` (repository `config/`).

## `permissions.yaml`

Rule-based gating for tool invocations. Patterns are **Python regex** strings matched against a derived check string (not raw JSON):

| Tool family | String matched |
|-------------|----------------|
| `bash`, `bash_background` | Shell command |
| `read`, `write`, `revert` | File path |
| `grep` | Synthetic `grep <pattern> <path> recursive=…` |
| `glob` | Glob pattern |
| Other / MCP | First input value (stringified) |

**Evaluation order:** `always_deny` → `always_allow` → `ask_user` (interactive `y/N` in the async path) → default allow.

Edit patterns to match your org’s risk tolerance. Dangerous fragments are also blocked inside `tools/builtin.py` for `bash`.

## `mcp_config.yaml`

Declares **stdio** MCP servers. Each entry under `servers` can include:

| Field | Notes |
|-------|--------|
| `name` | Logical server name; tools become `mcp__<name>__<tool>` |
| `transport` | Only `stdio` is implemented |
| `command` / `args` | Spawn line for the MCP server process |

The harness opens **all** configured servers inside one `AsyncExitStack` for the lifetime of `main.amain()`, so teardown stays in the same asyncio task (avoids cancel-scope issues with anyio).

**Requirements:** `pip install mcp` (see root `requirements.txt`). External binaries such as `npx` or `uvx` must exist on `PATH` if referenced.

Example servers in the sample file point at common MCP packages; uncomment or adjust for your environment.
