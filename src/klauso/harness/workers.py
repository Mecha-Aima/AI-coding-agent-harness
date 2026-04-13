import threading
import time
from typing import Any, Dict, List

from klauso.core.client import client
from klauso.core.settings import ENABLE_AUTONOMOUS_WORKERS, MODEL
from klauso.harness.tasks_todos import (
    claim_next_task,
    complete_task_board,
    fail_task_board,
)
from klauso.harness.tool_dispatch_sync import dispatch_tools_sync, extended_dispatch_map
from klauso.tools.schemas import EXTENDED_TOOLS

_worker_stop: threading.Event | None = None
_worker_threads: List[threading.Thread] = []


def _worker_loop(agent_id: str, stop: threading.Event) -> None:
    dispatch = extended_dispatch_map()
    print(f"\033[90m  [worker {agent_id}] autonomous loop started\033[0m")
    while not stop.is_set():
        task = claim_next_task(agent_id)
        if not task:
            time.sleep(1.0)
            continue
        tid = task["id"]
        prompt = f"Complete this claimed task [{tid}]:\n{task['description']}\nReturn a concise result summary."
        history: List[Dict[str, Any]] = [{"role": "user", "content": prompt}]
        try:
            while True:
                response = client.messages.create(
                    model=MODEL,
                    system="You are a background worker. Complete the claimed task using tools. Be concise.",
                    messages=history,
                    tools=EXTENDED_TOOLS,
                    max_tokens=4000,
                )
                history.append({"role": "assistant", "content": response.content})
                if response.stop_reason != "tool_use":
                    break
                results = dispatch_tools_sync(response.content, dispatch)
                history.append({"role": "user", "content": results})
            summary = "".join(
                block.text for block in history[-1]["content"] if hasattr(block, "text")
            )
            complete_task_board(tid, summary[:2000])
            print(f"\033[90m  [worker {agent_id}] completed {tid}\033[0m")
        except Exception as e:
            fail_task_board(tid, str(e))
            print(f"\033[31m  [worker {agent_id}] failed {tid}: {e}\033[0m")


def start_autonomous_workers(count: int = 2) -> None:
    global _worker_stop, _worker_threads
    if not ENABLE_AUTONOMOUS_WORKERS:
        return
    if _worker_stop is not None:
        return
    _worker_stop = threading.Event()
    for i in range(count):
        aid = f"worker-{i+1}"
        t = threading.Thread(target=_worker_loop, args=(aid, _worker_stop), daemon=True)
        t.start()
        _worker_threads.append(t)
    print(f"\033[90m  [workers] started {count} autonomous task workers\033[0m")


def stop_autonomous_workers() -> None:
    global _worker_stop, _worker_threads
    if _worker_stop is not None:
        _worker_stop.set()
        _worker_stop = None
        _worker_threads.clear()
