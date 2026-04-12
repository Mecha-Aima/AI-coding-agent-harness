import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple


def _git(args: List[str], cwd: str | None = None) -> Tuple[int, str, str]:
    result = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd or os.getcwd())
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _slug_task_id(task_id: str) -> str:
    """Filesystem-safe fragment derived from task_id (s12 used [:8]; longer avoids collisions)."""
    s = re.sub(r"[^\w\-.]+", "_", task_id).strip("._")
    return (s[:40] if s else "task") or "task"


def create_worktree(task_id: str) -> Tuple[str, str]:
    slug = _slug_task_id(task_id)
    branch_name = f"task/{slug}"
    worktree_path = str(Path(os.getcwd()).resolve().parent / f".worktree-{slug}")

    rc_git, _, err_git = _git(["rev-parse", "--is-inside-work-tree"])
    if rc_git != 0:
        raise RuntimeError(f"Not a git working tree: {err_git or 'git rev-parse failed'}")

    if Path(worktree_path).exists():
        shutil.rmtree(worktree_path, ignore_errors=True)
        _git(["worktree", "remove", "--force", worktree_path])

    def _worktree_add() -> Tuple[int, str, str]:
        return _git(["worktree", "add", "-b", branch_name, worktree_path])

    rc, out, err = _worktree_add()
    if rc != 0:
        print(f"\033[33m  [worktree] Branch conflict or stale state. Resetting branch: {branch_name}\033[0m")
        _git(["branch", "-D", branch_name])
        rc, out, err = _worktree_add()

    if rc != 0:
        raise RuntimeError(f"git worktree add failed (exit {rc}): {err or out or 'unknown error'}")

    if not Path(worktree_path).is_dir():
        raise RuntimeError(f"git worktree add reported success but path is missing: {worktree_path}")

    return worktree_path, branch_name


def remove_worktree(path: str, branch: str) -> None:
    _git(["worktree", "remove", "--force", path])
    p = Path(path)
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)
    _git(["branch", "-D", branch])


def run_worktree_create(task_id: str) -> str:
    try:
        path, branch = create_worktree(task_id)
        return f"Created worktree at {path} on branch {branch}"
    except Exception as e:
        return f"Error creating worktree: {e}"


def run_worktree_remove(path: str, branch: str) -> str:
    try:
        remove_worktree(path, branch)
        return f"Removed worktree {path} and branch {branch}"
    except Exception as e:
        return f"Error removing worktree: {e}"


WORKTREE_TOOLS_SCHEMA = [
    {
        "name": "worktree_create",
        "description": "Create a git worktree and branch for isolated work (task/<id>).",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "string", "description": "Unique task id string."}},
            "required": ["task_id"],
        },
    },
    {
        "name": "worktree_remove",
        "description": "Remove a git worktree and its branch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "branch": {"type": "string"},
            },
            "required": ["path", "branch"],
        },
    },
]
