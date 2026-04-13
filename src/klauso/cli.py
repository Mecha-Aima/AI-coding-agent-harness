import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

try:
    import readline  # noqa: F401
except ImportError:
    pass
try:
    from colorama import init as _ci

    _ci()
except ImportError:
    pass


def _bootstrap_cli_env() -> None:
    """Parse early CLI flags so KLAUSO_* is set before klauso.core.settings loads."""
    parser = argparse.ArgumentParser(prog="klauso", add_help=True)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace root (default: current directory). Sets KLAUSO_WORKSPACE.",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing permissions.yaml and mcp_config.yaml. Sets KLAUSO_CONFIG_DIR.",
    )
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=None,
        help="Skills directory (SKILL.md per folder). Sets KLAUSO_SKILLS_DIR.",
    )
    args, remainder = parser.parse_known_args()
    sys.argv = [sys.argv[0]] + remainder
    if args.workspace is not None:
        os.environ["KLAUSO_WORKSPACE"] = str(args.workspace.resolve())
    if args.config_dir is not None:
        os.environ["KLAUSO_CONFIG_DIR"] = str(args.config_dir.resolve())
    if args.skills_dir is not None:
        os.environ["KLAUSO_SKILLS_DIR"] = str(args.skills_dir.resolve())


async def amain() -> None:
    from klauso.core.settings import ENABLE_AUTONOMOUS_WORKERS, ENABLE_TEAMS, HARNESS_DEBUG
    from klauso.harness.background import drain_notifications
    from klauso.harness.cache import CacheStats
    from klauso.harness.events import register_default_hooks
    from klauso.harness import interrupts as interrupt_mod
    from klauso.harness.interrupts import STREAM_INTERRUPT_USER_TEXT, set_interrupt_queue
    from klauso.harness.loop import build_merged_tool_definitions, run_until_idle
    from klauso.harness.mcp_runtime import mcp_lifespan, mcp_tool_name_set
    from klauso.harness.sessions import (
        SESSIONS_DIR,
        create_new_session,
        load_session,
        print_sessions_table,
        save_session,
    )
    from klauso.harness.teams import start_teammate_threads, stop_teammate_threads
    from klauso.harness.workers import start_autonomous_workers, stop_autonomous_workers
    from klauso.memory.compaction import maybe_compact

    register_default_hooks()
    set_interrupt_queue(asyncio.Queue())

    print("\033[90mKlauso | Anthropic Messages + tools + MCP + teams\033[0m\n")

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
                        None, lambda: input(f"\033[36mklauso ({current_session['id']}) >> \033[0m").strip()
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


def main() -> None:
    _bootstrap_cli_env()
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
