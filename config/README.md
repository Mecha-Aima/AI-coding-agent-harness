# Configuration

YAML files are loaded from **`klauso.core.settings.CONFIG_DIR`**: by default `<workspace>/config/` after Klauso seeds missing files from `klauso.resources`. Override with **`KLAUSO_CONFIG_DIR`** or `klauso --config-dir`.

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

Destructive patterns belong in **`always_deny`**. Read-only **`git`** commands use explicit **`always_allow`** rules; any other **`git`** command matches **`ask_user`**. Dangerous fragments are also blocked inside `klauso.tools.builtin` for `bash`.

## `mcp_config.yaml`

Declares **stdio** MCP servers. Each entry under `servers` can include:

| Field | Notes |
|-------|--------|
| `name` | Logical server name; tools become `mcp__<name>__<tool>` |
| `transport` | Only `stdio` is implemented |
| `command` / `args` | Spawn line for the MCP server process |

The harness opens **all** configured servers inside one `AsyncExitStack` for the lifetime of the CLI `amain()` coroutine, so teardown stays in the same asyncio task (avoids cancel-scope issues with anyio).

**Requirements:** `mcp` is a dependency of the `klauso` package. External binaries such as `npx` must exist on `PATH` for the default filesystem and GitHub servers.

Default Klauso resources include **filesystem** and **GitHub** servers; add more entries under `servers:` for additional stdio MCP servers.
