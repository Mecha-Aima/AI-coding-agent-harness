"""
Mailbox JSONL handoff contract (lead <-> teammates):
Each line is JSON: {"from", "type", "body", "timestamp"}.
type is "request" | "reply". Single .mailboxes/<agent>.jsonl per agent; all writes/reads hold that agent's lock.
"""

import json
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import os

from klauso.core.client import client
from klauso.core.settings import MODEL
from klauso.harness.tool_dispatch_sync import dispatch_tools_sync, extended_dispatch_map
from klauso.tools.schemas import EXTENDED_TOOLS

MAILBOX_DIR = Path(".mailboxes")
_mail_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)

TEAMMATES: Dict[str, str] = {
    "explorer": (
        f"You are an explorer agent specializing in code comprehension at {os.getcwd()}. "
        "Your goal is to find relevant files, explain logic, and map dependencies. "
        "Use bash, read, glob, and grep to gather intelligence."
    ),
    "writer": (
        f"You are a writer agent specializing in file creation and editing at {os.getcwd()}. "
        "Your goal is to implement features, fix bugs, and document code. "
        "Use write, read, and bash to modify the environment."
    ),
}


def _mailbox_path(agent_name: str) -> Path:
    return MAILBOX_DIR / f"{agent_name}.jsonl"


def _send_message(to_agent: str, from_agent: str, body: str, msg_type: str = "request") -> None:
    MAILBOX_DIR.mkdir(exist_ok=True)
    path = _mailbox_path(to_agent)
    payload = {"from": from_agent, "type": msg_type, "body": body, "timestamp": time.time()}
    with _mail_locks[to_agent]:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")


def _receive_messages(agent_name: str) -> List[Dict[str, Any]]:
    path = _mailbox_path(agent_name)
    with _mail_locks[agent_name]:
        if not path.exists():
            return []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            messages = [json.loads(line) for line in lines if line.strip()]
            path.write_text("", encoding="utf-8")
            return messages
        except (json.JSONDecodeError, OSError) as e:
            print(f"\033[31m  [error] Mailbox read failed for {agent_name}: {e}\033[0m")
            return []


def run_send_to_teammate(name: str, message: str) -> str:
    if name not in TEAMMATES:
        return f"Error: '{name}' is not a recognized teammate."
    _send_message(to_agent=name, from_agent="lead", body=message, msg_type="request")
    print(f"\033[90m  [lead] waiting for {name} to reply...\033[0m")
    for _ in range(120):
        time.sleep(0.5)
        replies = _receive_messages("lead")
        if replies:
            return "\n\n".join(f"Response from {r['from']}:\n{r['body']}" for r in replies)
    return f"Timeout: Teammate '{name}' did not respond within 60 seconds."


def run_list_teammates() -> str:
    return "\n".join(f"  - {n}: {s[:80]}..." for n, s in TEAMMATES.items())


def _run_teammate_loop(name: str, specialist_prompt: str, stop_event: threading.Event) -> None:
    dispatch = extended_dispatch_map()
    print(f"\033[90m  [{name}] thread initialized and ready\033[0m")
    while not stop_event.is_set():
        incoming = _receive_messages(name)
        for msg in incoming:
            sender = msg["from"]
            task_body = msg["body"]
            print(f"\033[35m  [{name}] processing task from {sender}: {task_body[:60]}...\033[0m")
            sub_history: List[Dict[str, Any]] = [{"role": "user", "content": task_body}]
            while True:
                response = client.messages.create(
                    model=MODEL,
                    system=specialist_prompt,
                    messages=sub_history,
                    tools=EXTENDED_TOOLS,
                    max_tokens=4000,
                )
                sub_history.append({"role": "assistant", "content": response.content})
                if response.stop_reason != "tool_use":
                    break
                results = dispatch_tools_sync(response.content, dispatch)
                sub_history.append({"role": "user", "content": results})
            final_text = "".join(
                block.text for block in sub_history[-1]["content"] if hasattr(block, "text")
            )
            _send_message(to_agent=sender, from_agent=name, body=final_text, msg_type="reply")
            print(f"\033[35m  [{name}] result sent back to {sender}\033[0m")
        stop_event.wait(timeout=0.5)


TEAM_TOOLS_SCHEMA = [
    {
        "name": "send_to_teammate",
        "description": "Delegate a subtask to a specialist teammate. This blocks until they reply.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "enum": list(TEAMMATES.keys())},
                "message": {"type": "string", "description": "Specific tasks/instructions."},
            },
            "required": ["name", "message"],
        },
    },
    {
        "name": "list_teammates",
        "description": "List all currently available specialist agents and their roles.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

_team_stop: Optional[threading.Event] = None
_team_threads: List[threading.Thread] = []


def start_teammate_threads() -> None:
    global _team_stop, _team_threads
    if _team_stop is not None:
        return
    MAILBOX_DIR.mkdir(exist_ok=True)
    _team_stop = threading.Event()
    for agent_name, agent_prompt in TEAMMATES.items():
        t = threading.Thread(
            target=_run_teammate_loop,
            args=(agent_name, agent_prompt, _team_stop),
            daemon=True,
        )
        t.start()
        _team_threads.append(t)
    print(f"\033[90m  [team] started teammates: {', '.join(TEAMMATES)}\033[0m")


def stop_teammate_threads() -> None:
    global _team_stop, _team_threads
    if _team_stop is not None:
        _team_stop.set()
        _team_stop = None
        _team_threads.clear()
    for agent in list(TEAMMATES.keys()) + ["lead"]:
        p = _mailbox_path(agent)
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass
