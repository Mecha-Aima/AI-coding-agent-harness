import json
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

TODO_FILE = ".agent_todo.json"
TASKS_FILE = Path(".agent_tasks.json")

tasks_board_lock = threading.Lock()
_tasks_file_lock = tasks_board_lock


def run_todo_write(tasks: List[str]) -> str:
    data = [{"id": i, "task": t, "status": "pending"} for i, t in enumerate(tasks)]
    with open(TODO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    lines = "\n".join(f"  [{i}] {t}" for i, t in enumerate(tasks))
    return f"Plan written ({len(tasks)} tasks):\n{lines}"


def run_todo_read() -> str:
    try:
        with open(TODO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return "\n".join(f"[{t['id']}] [{t['status']:12s}] {t['task']}" for t in data)
    except FileNotFoundError:
        return "(no todo list found - please use todo_write first)"
    except Exception as e:
        return f"Error reading todo list: {e}"


def run_todo_update(index: int, status: str) -> str:
    try:
        with open(TODO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if 0 <= index < len(data):
            data[index]["status"] = status
            with open(TODO_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return f"Updated task {index} status to: {status}"
        return f"Error: Task index {index} is out of range."
    except FileNotFoundError:
        return "Error: No todo list found to update."
    except Exception as e:
        return f"Error during todo_update: {e}"


def _load_tasks_unlocked() -> List[Dict[str, Any]]:
    if not TASKS_FILE.exists():
        return []
    try:
        return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _load_tasks() -> List[Dict[str, Any]]:
    with _tasks_file_lock:
        return _load_tasks_unlocked()


def _save_tasks(tasks: List[Dict[str, Any]]) -> None:
    with _tasks_file_lock:
        try:
            TASKS_FILE.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
        except OSError as e:
            print(f"\033[31m[error] Failed to save tasks: {e}\033[0m")


def run_task_create(description: str, depends_on: Optional[List[str]] = None, priority: str = "medium") -> str:
    with _tasks_file_lock:
        tasks: List[Dict[str, Any]] = []
        if TASKS_FILE.exists():
            try:
                tasks = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                tasks = []
        task_id = uuid.uuid4().hex[:8]
        new_task = {
            "id": task_id,
            "description": description,
            "status": "pending",
            "priority": priority,
            "depends_on": depends_on or [],
            "result": "",
        }
        tasks.append(new_task)
        try:
            TASKS_FILE.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
        except OSError as e:
            return f"Error saving task: {e}"
    return f"Created task {task_id}: {description}"


def run_task_list() -> str:
    tasks = _load_tasks()
    if not tasks:
        return "(no tasks currently in the system)"
    lines = []
    for t in tasks:
        deps_str = f" [needs: {','.join(t['depends_on'])}]" if t.get("depends_on") else ""
        line = f"[{t['id']}] [{t['status']:12s}] [{t['priority']:6s}]{deps_str} {t['description']}"
        lines.append(line)
    return "\n".join(lines)


def run_task_update(task_id: str, status: str, result: str = "") -> str:
    with _tasks_file_lock:
        tasks = _load_tasks_unlocked()
        if not tasks and not TASKS_FILE.exists():
            return "Error: No tasks file."
        found = False
        actual_id = ""
        for t in tasks:
            if t["id"].startswith(task_id):
                t["status"] = status
                if result:
                    t["result"] = result
                found = True
                actual_id = t["id"]
                break
        if found:
            TASKS_FILE.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
            return f"Task {actual_id} successfully updated to '{status}'"
    return f"Error: Task with ID '{task_id}' not found."


def run_task_next() -> str:
    tasks = _load_tasks()
    done_ids: Set[str] = {t["id"] for t in tasks if t["status"] == "done"}
    for t in tasks:
        if t["status"] != "pending":
            continue
        dependencies = t.get("depends_on", [])
        if all(dep in done_ids for dep in dependencies):
            return f"Suggested Next Task: [{t['id']}] (Priority: {t['priority']}) - {t['description']}"
    return "No unblocked tasks available. Either all tasks are done or there is a dependency circularity."


def claim_next_task(agent_id: str) -> Optional[Dict[str, Any]]:
    with tasks_board_lock:
        tasks = _load_tasks_unlocked()
        done_ids = {t["id"] for t in tasks if t["status"] == "done"}
        for t in tasks:
            if t["status"] != "pending":
                continue
            dependencies = t.get("depends_on", [])
            if all(dep in done_ids for dep in dependencies):
                t["status"] = "in_progress"
                t["claimed_by"] = agent_id
                try:
                    TASKS_FILE.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
                except OSError:
                    return None
                return dict(t)
    return None


def complete_task_board(task_id: str, result: str) -> None:
    with tasks_board_lock:
        tasks = _load_tasks_unlocked()
        for t in tasks:
            if t["id"] == task_id:
                t["status"] = "done"
                t["result"] = result
                TASKS_FILE.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
                break


def fail_task_board(task_id: str, error_message: str) -> None:
    with tasks_board_lock:
        tasks = _load_tasks_unlocked()
        for t in tasks:
            if t["id"] == task_id:
                t["status"] = "failed"
                t["result"] = error_message
                TASKS_FILE.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
                break


TODO_TOOLS_SCHEMA = [
    {
        "name": "todo_write",
        "description": "Write a multi-step todo plan before starting a task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "A list of sequential steps to complete the goal.",
                }
            },
            "required": ["tasks"],
        },
    },
    {
        "name": "todo_read",
        "description": "Read the current todo list to check progress.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "todo_update",
        "description": "Update the status of a specific task in the plan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index": {"type": "integer", "description": "The 0-based index of the task."},
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "done"],
                    "description": "The new status of the task.",
                },
            },
            "required": ["index", "status"],
        },
    },
]

TASK_TOOLS_SCHEMA = [
    {
        "name": "task_create",
        "description": "Create a new task in the persistent dependency graph.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "What needs to be done."},
                "depends_on": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of task IDs this task depends on.",
                },
                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
            },
            "required": ["description"],
        },
    },
    {
        "name": "task_list",
        "description": "Show all tasks, their IDs, status, and dependency requirements.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "task_update",
        "description": "Change the status of a task or record its final result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "8-char ID of the task."},
                "status": {"type": "string", "enum": ["pending", "in_progress", "done", "failed"]},
                "result": {"type": "string", "description": "Brief summary of work done."},
            },
            "required": ["task_id", "status"],
        },
    },
    {
        "name": "task_next",
        "description": "Consult the graph logic to find the next task that is not blocked by dependencies.",
        "input_schema": {"type": "object", "properties": {}},
    },
]
