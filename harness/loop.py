import asyncio
import copy
import uuid
from collections.abc import Mapping
from typing import Any, Awaitable, Callable, Dict, List, Set, Tuple

import anthropic

from core.client import client
from core.settings import CACHE_MODE, HARNESS_DEBUG, MODEL
from harness.background import run_bash_background
from harness.cache import CacheStats, apply_cache_to_tools, build_cached_system, default_cacheable_system_text
from harness.events import bus
from harness import interrupts as interrupt_mod
from harness.interrupts import (
    clear_stream_abort,
    drain_interrupts,
    install_sigint_for_stream_abort,
    restore_sigint,
    stream_abort_event,
)
from harness.mcp_runtime import execute_mcp_tool
from harness.skills_meta import run_list_skills, run_load_skill
from harness.tasks_todos import (
    TASK_TOOLS_SCHEMA,
    TODO_TOOLS_SCHEMA,
    run_task_create,
    run_task_list,
    run_task_next,
    run_task_update,
    run_todo_read,
    run_todo_update,
    run_todo_write,
)
from harness.teams import run_list_teammates, run_send_to_teammate
from harness.worktrees import run_worktree_create, run_worktree_remove
from subagents.runner import run_subagent
from tools import builtin
from tools.permissions import check_permission_async, load_rules, permission_check_string
from tools.schemas import EXTENDED_TOOLS


def build_merged_tool_definitions(mcp_extra: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from harness.background import BG_TOOL_SCHEMA
    from harness.skills_meta import SKILL_TOOLS_SCHEMA
    from harness.teams import TEAM_TOOLS_SCHEMA
    from harness.worktrees import WORKTREE_TOOLS_SCHEMA
    from subagents.runner import SUBAGENT_TOOL_SCHEMA

    tools: List[Dict[str, Any]] = []
    tools.extend(copy.deepcopy(EXTENDED_TOOLS))
    tools.extend(TODO_TOOLS_SCHEMA)
    tools.extend(TASK_TOOLS_SCHEMA)
    tools.extend(SKILL_TOOLS_SCHEMA)
    tools.append(BG_TOOL_SCHEMA)
    tools.extend(TEAM_TOOLS_SCHEMA)
    tools.extend(WORKTREE_TOOLS_SCHEMA)
    tools.append(SUBAGENT_TOOL_SCHEMA)
    tools.extend(mcp_extra)
    return tools


def build_async_dispatch() -> Dict[str, Callable[[Dict[str, Any]], Awaitable[str]]]:
    return {
        "bash": lambda inp: builtin.async_bash(inp["command"]),
        "read": lambda inp: builtin.async_read(inp["path"], inp.get("start_line"), inp.get("end_line")),
        "write": lambda inp: builtin.async_write(inp["path"], inp["content"]),
        "grep": lambda inp: builtin.async_grep(inp["pattern"], inp.get("path", "."), inp.get("recursive", True)),
        "glob": lambda inp: builtin.async_glob(inp["pattern"]),
        "revert": lambda inp: builtin.async_revert(inp["path"]),
        "todo_write": lambda inp: asyncio.to_thread(run_todo_write, inp["tasks"]),
        "todo_read": lambda inp: asyncio.to_thread(run_todo_read),
        "todo_update": lambda inp: asyncio.to_thread(run_todo_update, inp["index"], inp["status"]),
        "task_create": lambda inp: asyncio.to_thread(
            run_task_create, inp["description"], inp.get("depends_on"), inp.get("priority", "medium")
        ),
        "task_list": lambda inp: asyncio.to_thread(run_task_list),
        "task_update": lambda inp: asyncio.to_thread(run_task_update, inp["task_id"], inp["status"], inp.get("result", "")),
        "task_next": lambda inp: asyncio.to_thread(run_task_next),
        "list_skills": lambda inp: asyncio.to_thread(run_list_skills),
        "load_skill": lambda inp: asyncio.to_thread(run_load_skill, inp["name"]),
        "bash_background": lambda inp: asyncio.to_thread(run_bash_background, inp["command"], inp.get("label") or None),
        "send_to_teammate": lambda inp: asyncio.to_thread(run_send_to_teammate, inp["name"], inp["message"]),
        "list_teammates": lambda inp: asyncio.to_thread(run_list_teammates),
        "worktree_create": lambda inp: asyncio.to_thread(run_worktree_create, inp["task_id"]),
        "worktree_remove": lambda inp: asyncio.to_thread(run_worktree_remove, inp["path"], inp["branch"]),
        "spawn_subagent": lambda inp: asyncio.to_thread(run_subagent, inp["prompt"]),
    }


async def dispatch_one_tool(
    block: Any,
    mcp_names: Set[str],
    async_dispatch: Dict[str, Callable[[Dict[str, Any]], Awaitable[str]]],
    rules: dict,
) -> Tuple[str, str]:
    tool_name = block.name
    tool_input = block.input
    inp_dict: Dict[str, Any] = dict(tool_input) if isinstance(tool_input, Mapping) else {}
    input_str = permission_check_string(tool_name, inp_dict)
    first_val = str(list(tool_input.values())[0])[:80] if tool_input else ""

    pre = bus.emit("pre_tool_use", tool=tool_name, input=tool_input)
    if any(isinstance(r, dict) and r.get("block") for r in pre):
        return block.id, "Error: Execution blocked by system security hook."

    allowed, reason = await check_permission_async(tool_name, input_str, rules)
    if not allowed:
        bus.emit("permission_denied", tool=tool_name, input=tool_input, reason=str(reason))
        return block.id, str(reason)

    print(f"\033[33m[{tool_name}] {first_val}...\033[0m")
    try:
        if tool_name in mcp_names:
            output = await execute_mcp_tool(tool_name, tool_input)
        else:
            handler = async_dispatch.get(tool_name)
            output = await handler(tool_input) if handler else f"Error: Unknown tool '{tool_name}'"
        bus.emit("post_tool_use", tool=tool_name, input=tool_input, output=output)
    except Exception as e:
        bus.emit("tool_error", tool=tool_name, error=str(e))
        output = f"Execution Error: {e}"
    print(str(output)[:200])
    return block.id, str(output)


async def run_until_idle(
    messages: List[Dict[str, Any]],
    all_tools: List[Dict[str, Any]],
    mcp_names: Set[str],
    stats: CacheStats,
) -> None:
    rules = load_rules()
    async_dispatch = build_async_dispatch()
    use_cache = CACHE_MODE == "anthropic"
    system_arg: Any = build_cached_system(default_cacheable_system_text()) if use_cache else default_cacheable_system_text()
    tools_arg = apply_cache_to_tools(all_tools) if use_cache else all_tools

    bus.emit("session_start")
    try:
        while True:
            for msg in await drain_interrupts():
                print(f"\n\033[31m[INTERRUPT] {msg}\033[0m")
                messages.append({"role": "user", "content": msg})

            print("\n\033[36m> Thinking...\033[0m")

            loop = asyncio.get_running_loop()
            clear_stream_abort()
            prev_sig = install_sigint_for_stream_abort(loop)

            def _blocking_stream() -> Any:
                with client.messages.stream(
                    model=MODEL,
                    system=system_arg,
                    messages=messages,
                    tools=tools_arg,
                    max_tokens=8000,
                ) as stream:
                    for text in stream.text_stream:
                        if stream_abort_event.is_set():
                            break
                        print(text, end="", flush=True)
                    return stream.get_final_message()

            try:
                response = await loop.run_in_executor(None, _blocking_stream)
            except anthropic.BadRequestError as exc:
                print(f"\n\033[31m[API ERROR] {exc}\033[0m")
                print(
                    "\033[33m  Hint: the session history may contain stale SDK fields.\n"
                    "  Start a new session or check the saved JSON for unexpected keys.\033[0m"
                )
                return
            except anthropic.APIError as exc:
                print(f"\n\033[31m[API ERROR] {exc}\033[0m")
                return
            finally:
                restore_sigint(prev_sig)

            if stream_abort_event.is_set():
                print("\033[33m\n  [interrupt] Streaming stopped (Ctrl+C).\033[0m")

            print()
            if hasattr(response, "usage") and use_cache:
                stats.record(response.usage)
                stats.show_turn(response.usage)

            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                return

            skip_tools = False
            for msg in await drain_interrupts():
                print(f"\n\033[31m[INTERRUPT] Stopping before tool execution: {msg}\033[0m")
                messages.append({"role": "user", "content": msg})
                skip_tools = True
            if skip_tools:
                continue

            tool_blocks = [b for b in response.content if b.type == "tool_use"]
            if HARNESS_DEBUG and tool_blocks:
                depth = interrupt_mod.interrupt_queue.qsize() if interrupt_mod.interrupt_queue else 0
                batch = uuid.uuid4().hex[:8]
                print(
                    f"\033[90m  [debug] tool_batch={batch} n={len(tool_blocks)} interrupt_queue_depth={depth}\033[0m"
                )
            pairs = await asyncio.gather(
                *[dispatch_one_tool(b, mcp_names, async_dispatch, rules) for b in tool_blocks]
            )
            results_map = dict(pairs)
            turn_results = [
                {"type": "tool_result", "tool_use_id": b.id, "content": results_map[b.id]} for b in tool_blocks
            ]
            messages.append({"role": "user", "content": turn_results})
    finally:
        bus.emit("session_end")
