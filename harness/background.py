import queue
import subprocess
import threading
from typing import Any, Dict, List, Optional

import os

_NOTIFY_QUEUE: queue.Queue = queue.Queue()


def run_bash_background(command: str, label: Optional[str] = None) -> str:
    task_label = label or command[:40]

    def _worker_logic() -> None:
        print(f"\033[90m  [bg] started: {task_label}\033[0m")
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=os.getcwd(),
            )
            output = (result.stdout + result.stderr).strip()[:2000] or "(no output)"
            status = "completed"
        except subprocess.TimeoutExpired:
            output = "Error: Process exceeded 300s timeout limit."
            status = "timed out"
        except Exception as e:
            output = f"Error: Unexpected failure during execution: {e}"
            status = "failed"
        notification = f"[Background task '{task_label}' {status}]\n{output}"
        _NOTIFY_QUEUE.put(notification)

    threading.Thread(target=_worker_logic, daemon=True).start()
    return f"Background task started: '{task_label}'. You will be notified when it finishes."


def drain_notifications() -> List[Dict[str, str]]:
    notifs: List[Dict[str, str]] = []
    while not _NOTIFY_QUEUE.empty():
        try:
            msg = _NOTIFY_QUEUE.get_nowait()
            print(f"\033[90m  [bg] notification received: {msg[:80]}...\033[0m")
            notifs.append({"role": "user", "content": msg})
        except queue.Empty:
            break
    return notifs


BG_TOOL_SCHEMA = {
    "name": "bash_background",
    "description": "Run a shell command in the background. Useful for long-running scripts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The command line string to execute."},
            "label": {"type": "string", "description": "A short identifier for the notification."},
        },
        "required": ["command"],
    },
}
