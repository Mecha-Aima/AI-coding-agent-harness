import asyncio
import sys
import uuid
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    import readline  # noqa: F401
except ImportError:
    pass
try:
    from colorama import init as _ci

    _ci()
except ImportError:
    pass

from core.settings import ENABLE_AUTONOMOUS_WORKERS, ENABLE_TEAMS, HARNESS_DEBUG
from harness.background import drain_notifications
from harness.cache import CacheStats
from harness.events import register_default_hooks
from harness import interrupts as interrupt_mod
from harness.interrupts import STREAM_INTERRUPT_USER_TEXT, set_interrupt_queue
from harness.loop import build_merged_tool_definitions, run_until_idle
from harness.mcp_runtime import mcp_lifespan, mcp_tool_name_set
from harness.sessions import (
    SESSIONS_DIR,
    create_new_session,
    load_session,
    print_sessions_table,
    save_session,
)
from harness.teams import start_teammate_threads, stop_teammate_threads
from harness.workers import start_autonomous_workers, stop_autonomous_workers
from memory.compaction import maybe_compact


async def amain() -> None:
    register_default_hooks()
    set_interrupt_queue(asyncio.Queue())

    print("\033[90mUnified coding agent | Anthropic Messages + tools + MCP + teams\033[0m\n")

    # mcp_lifespan() keeps every stdio subprocess and anyio task group alive
    # inside this coroutine, so cancel scopes are never crossed between tasks.
    async with mcp_lifespan() as mcp_extra:
        all_tools = build_merged_tool_definitions(mcp_extra)
        mcp_names = mcp_tool_name_set()
        stats = CacheStats()
        if HARNESS_DEBUG:
            print(f"\033[90m  [debug] tools={len(all_tools)} mcp={len(mcp_names)}\033[0m")

        if ENABLE_TEAMS:
            start_teammate_threads()
        start_autonomous_workers(2)

        current_session = create_new_session()
        print(f"  Session \033[36m{current_session['id']}\033[0m — commands: :sessions :resume :fork :title :save\n")
        if HARNESS_DEBUG:
            sp = SESSIONS_DIR / f"{current_session['id']}.json"
            print(f"\033[90m  [debug] session_file={sp.resolve()}\033[0m\n")

        loop = asyncio.get_event_loop()
        active_task: asyncio.Task | None = None

        try:
            while True:
                try:
                    query = await loop.run_in_executor(
                        None, lambda: input(f"\033[36magent ({current_session['id']}) >> \033[0m").strip()
                    )
                except (EOFError, KeyboardInterrupt):
                    save_session(current_session)
                    print(f"\n  Session {current_session['id']} saved. Goodbye.")
                    break

                if query.lower() in ("q", "exit", "quit"):
                    save_session(current_session)
                    print(f"  Session {current_session['id']} saved.")
                    break

                if query == ":sessions":
                    print_sessions_table()
                    continue
                if query.startswith(":resume "):
                    tid = query[8:].strip()
                    loaded = load_session(tid)
                    if loaded:
                        current_session = loaded
                        print(f"  Resumed \033[36m{current_session['id']}\033[0m — {current_session['title']}")
                    else:
                        print(f"  Not found: {tid}")
                    continue
                if query.startswith(":fork "):
                    sid = query[6:].strip()
                    src = load_session(sid)
                    if src:
                        new_id = uuid.uuid4().hex[:8]
                        current_session = {
                            **src,
                            "id": new_id,
                            "title": f"Fork of {src['title'][:30]}",
                            "created": datetime.now().isoformat(),
                            "updated": datetime.now().isoformat(),
                        }
                        save_session(current_session)
                        print(f"  Forked → \033[36m{new_id}\033[0m")
                    else:
                        print(f"  Not found: {sid}")
                    continue
                if query.startswith(":title "):
                    current_session["title"] = query[7:].strip()
                    save_session(current_session)
                    print(f"  Title: {current_session['title']}")
                    continue
                if query == ":save":
                    save_session(current_session)
                    print("  Saved.")
                    continue

                for n in drain_notifications():
                    current_session["messages"].append(n)
                maybe_compact(current_session["messages"])

                if not current_session["messages"]:
                    current_session["title"] = query[:50]

                current_session["messages"].append({"role": "user", "content": query})

                active_task = asyncio.create_task(
                    run_until_idle(current_session["messages"], all_tools, mcp_names, stats)
                )
                try:
                    await active_task
                except asyncio.CancelledError:
                    pass
                except KeyboardInterrupt:
                    if interrupt_mod.interrupt_queue is not None:
                        await interrupt_mod.interrupt_queue.put(STREAM_INTERRUPT_USER_TEXT)
                        print("\033[31m\n  Interrupt queued — agent will pick up after current step.\033[0m")
                        try:
                            await asyncio.wait_for(active_task, timeout=30)
                        except (asyncio.TimeoutError, asyncio.CancelledError):
                            if not active_task.done():
                                active_task.cancel()
                save_session(current_session)
                print()
        finally:
            stats.summary()
            stop_teammate_threads()
            stop_autonomous_workers()
            # mcp_lifespan().__aexit__ runs here automatically, in this same task


def main() -> None:
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
