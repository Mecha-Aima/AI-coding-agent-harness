# Klauso manual testing guide

Use this in a **directory that is not this repository** (a fresh clone of another project, or an empty scratch folder with a throwaway git repo). That validates real-world `pip install klauso` behavior, `.env`, `config/`, and MCP.

---

## Prerequisites

- **Python 3.11+**
- **Node.js** and **npm** on `PATH` (default MCP uses `npx` for filesystem and GitHub servers).
- **Anthropic API key**
- Optional: **GitHub PAT** in `.env` as `GITHUB_TOKEN=` for GitHub MCP tools.

---

## 1. Install the package

### From PyPI (after publish)

```bash
python3 -m venv .venv-klauso
source .venv-klauso/bin/activate   # Windows: .venv-klauso\Scripts\activate
pip install -U pip
pip install klauso
klauso --help
```

You should see `usage: klauso` and flags `--workspace`, `--config-dir`, `--skills-dir`.

### From a local wheel (before PyPI or for QA)

On a machine with the repo:

```bash
cd /path/to/AI-coding-agent-harness
python3 -m pip install build
rm -rf dist && python3 -m build
```

Copy `dist/klauso-*.whl` to the test workspace, then:

```bash
python3 -m venv .venv-klauso
source .venv-klauso/bin/activate
pip install /path/to/klauso-0.1.0-py3-none-any.whl
klauso --help
```

---

## 2. Environment configuration

In your **test workspace** (the folder where you will run `klauso`):

1. Create `.env` (copy from the [`.env.example`](../.env.example) in the Klauso repo if needed).

2. **Minimum required:**

   ```env
   ANTHROPIC_API_KEY=sk-ant-api03-...
   ```

3. **Recommended for defaults:**

   ```env
   MODEL_ID=claude-sonnet-4-5-20250929
   CACHE_MODE=anthropic
   ENABLE_TEAMS=1
   ENABLE_AUTONOMOUS_WORKERS=0
   ```

4. **GitHub MCP** (if you will test `mcp__github__*` tools):

   ```env
   GITHUB_TOKEN=ghp_...
   ```

5. **Optional path overrides** (non-default layout):

   ```env
   KLAUSO_WORKSPACE=/absolute/path/to/project
   KLAUSO_CONFIG_DIR=/absolute/path/to/config_folder
   KLAUSO_SKILLS_DIR=/absolute/path/to/skills
   ```

6. **Proxy / LiteLLM:**

   ```env
   ANTHROPIC_BASE_URL=https://...
   CACHE_MODE=off
   ```

Klauso loads **`<workspace>/.env`** first (workspace = current directory or `KLAUSO_WORKSPACE` / `--workspace`).

---

## 3. Running Klauso

```bash
cd /your/test/workspace
source /path/to/.venv-klauso/bin/activate
klauso
```

Alternate:

```bash
klauso --workspace /your/test/workspace
```

First run: if `./config/` is missing or empty of YAML, Klauso **seeds** `permissions.yaml` and `mcp_config.yaml`. If `./skills/` is empty, **bundled** skills from the package are used.

Exit: `q`, `exit`, or `quit` (session saves).

---

## 4. REPL meta-commands (smoke)

Run these as **exact lines** at the `klauso (...) >>` prompt:

| Step | Input | Expect |
|------|--------|--------|
| List sessions | `:sessions` | Table or empty list |
| Save | `:save` | `Saved.` |
| Title | `:title My smoke test` | Title echoed |
| Quit | `q` | Session saved, exit |

After at least one user message, note the session id, restart `klauso`, then:

| Step | Input | Expect |
|------|--------|--------|
| Resume | `:resume <id>` | Session loads |
| Fork | `:fork <id>` | New id |
| Sessions again | `:sessions` | Shows sessions |

---

## 5. Isolated prompts (one capability each)

Ask the model **verbatim or close**; it should pick the right tools. Replace paths with files that exist in **your** test workspace.

### Filesystem: `read`

> Open the file `README.md` in this workspace and summarize the first 30 lines.

### Filesystem: `write` + `revert`

> Create a new file `klauso_smoke.txt` with the single line `version 1`, then read it back to confirm.

Then:

> Overwrite `klauso_smoke.txt` with `version 2`, then use revert if available to restore the previous content and show what you get.

### Filesystem: `glob`

> List all Python files under the current directory (use glob, not find).

### Filesystem: `grep`

> Search this repo for the string `TODO` in `*.md` files and list matching paths.

### Shell: `bash` (read-only)

> Run `pwd` and `ls -la` in the project root and paste the output.

### Shell: read-only git

> Run `git status` and summarize branch and dirty state.

### Shell: permission `ask_user` (git write)

> Stage all changes and create a git commit with message `chore: klauso manual test` (only if I confirm at the prompt).

When the harness shows **Allow? [y/N]**, type `n` unless you intend to commit.

### Shell: `always_deny`

> Run `sudo ls /root` and report the result.

Expect denial / error from policy or builtin, not a successful root listing.

### Planning: todos

> Use the todo tools: add tasks (1) verify read (2) verify write (3) verify grep; then read todos back; mark the first as completed.

### Planning: task graph

> Create a task "Manual test task A" with medium priority, list all tasks, then mark that task completed with a short result string.

### Skills

> Call list_skills, then load_skill for `agent-builder` and tell me one bullet from the skill.

### Background bash

> Start a background shell job that runs `sleep 3 && echo done-bg` with a label `smoke-sleep`. Then tell me to press Enter on the next line.

On the **next** REPL line, type anything short; a notification may append about the job.

### Teams (requires `ENABLE_TEAMS=1`)

> List teammates, then send a short hello message to `explorer` (or the first teammate name returned).

Skip if teams are disabled.

### Worktrees (git repo only)

> List git worktrees if any; do not create one unless I ask.

Optional, safer follow-up in a disposable branch:

> Create a git worktree for a trivial path only if the repo is clean; otherwise only explain worktree_create.

### Subagent

> Use spawn_subagent with a prompt that only reads `README.md` and returns a one-sentence summary — no writes, no bash beyond read-only.

### MCP filesystem

> Using an MCP filesystem tool if available, list the top-level entries of the workspace root `.` .

### MCP GitHub

> Using an MCP GitHub tool if available, search or describe my user’s public repos (read-only). If tools fail, paste the error.

### Compaction / memory (long session)

> Repeat back a 400-word lorem ipsum I will paste in my next message, then summarize it in 20 words.

Paste a long block in the next turn; later turns may trigger compaction (`.agent_memory.md`). Optional stress test.

---

## 6. Compound prompts (multiple tools / features in one turn)

Use these **single** user messages to test batching and orchestration.

### Read + glob + grep

> In one turn: find all `*.py` files under `.`, grep for `def ` in `src` or the main package tree only, and read the first 40 lines of the main entry module you discover.

### Write + read + todo

> Create `compound_a.txt` with text `compound test`, read it to verify, and add a todo item "verify compound_a.txt exists".

### Task + bash

> Create a task "Run pwd check", mark it in progress using task tools, run `pwd` via bash, then mark the task completed with the pwd output as the result.

### Skills + filesystem

> Load the `code-review` skill, then read any single source file under 80 lines that the skill would plausibly review and state its path.

### Subagent + lead summary

> Spawn a subagent whose only job is to count how many `*.py` files are in the repo using read/glob only; when it returns, give me one number and the method used.

### MCP + filesystem (if MCP connected)

> List MCP tools whose names start with `mcp__filesystem`; call one read-only operation on `./README.md` or the workspace README; if that fails, call a bash `head -5 README.md` instead.

### Governance mix (allowed + denied in same request)

> Run `echo ok` via bash, then try `sudo id`; report both outcomes. Do not retry denied commands.

Expect first succeeds, second blocked or denied.

### Session + work (then REPL)

> Write a file `session_marker.txt` with the current session id you infer from context or say unknown, then remind me to run `:save` and `:sessions`.

Then manually run `:save` and `:sessions`.

### Background + next-line drain

> Start `bash_background` with `sleep 2 && echo wake`. I will send a blank line next; tell me if a notification appeared.

Send a blank or short line on the next prompt.

### Teams + todo (if teams on)

> Send a one-line status to teammate `explorer` and add a todo "notified explorer".

---

## 7. Interrupts (optional)

- During model **streaming**: press **Ctrl+C** once; stream should stop; you may see interrupt messaging.
- During **tool execution**: Ctrl+C may queue an interrupt for after the step (see README).

---

## 8. Checklist summary

- [ ] `klauso --help` works after install  
- [ ] `.env` with `ANTHROPIC_API_KEY` in workspace  
- [ ] First `klauso` run seeds or finds `config/*.yaml`  
- [ ] At least one full model turn with tools  
- [ ] `:save` / `:resume` cycle  
- [ ] One compound prompt from section 6  
- [ ] (Optional) MCP servers connect or fail loudly with useful stderr  
- [ ] (Optional) `GITHUB_TOKEN` for GitHub MCP  

---

## 9. Reporting issues

Note: Klauso version (`pip show klauso`), Python version, OS, whether PyPI or wheel install, and redact API keys when pasting logs.
