import asyncio
import glob as _glob
import os
import subprocess
from typing import Any, Dict, List, Optional

SNAPSHOTS: Dict[str, Optional[str]] = {}

_ALWAYS_BLOCK: List[str] = [
    "rm -rf /",
    "sudo",
    "shutdown",
    "reboot",
    "> /dev/",
    ":(){ :|:& };:",
]


def run_bash(command: str) -> str:
    if any(blocked in command for blocked in _ALWAYS_BLOCK):
        return "Error: dangerous command blocked"
    try:
        result = subprocess.run(
            command, shell=True, cwd=os.getcwd(), capture_output=True, text=True, timeout=120
        )
        output = (result.stdout + result.stderr).strip()
        return output[:50000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: timeout (120s)"
    except Exception as e:
        return f"Error: {e}"


def run_read(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        start_index = (start_line or 1) - 1
        end_index = end_line or len(lines)
        numbered_lines = "".join(
            f"{start_index + 1 + i:4d}\t{line}" for i, line in enumerate(lines[start_index:end_index])
        )
        return numbered_lines[:50000] or "(empty file)"
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except Exception as e:
        return f"Error reading {path}: {e}"


def run_write(path: str, content: str) -> str:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                SNAPSHOTS[path] = f.read()
            action = "updated"
        else:
            SNAPSHOTS[path] = None
            action = "created"
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"{action}: {path} (snapshot saved — use revert to undo)"
    except Exception as e:
        return f"Error writing {path}: {e}"


def run_grep(pattern: str, path: str = ".", recursive: bool = True) -> str:
    try:
        flags = ["-r"] if recursive else []
        result = subprocess.run(
            ["grep", "-n", *flags, pattern, path], capture_output=True, text=True, timeout=30
        )
        return ((result.stdout + result.stderr).strip() or "(no matches)")[:10000]
    except FileNotFoundError:
        try:
            command = f'findstr /S /N "{pattern}" "{path}\\*.py" "{path}\\*.js" "{path}\\*.md"'
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            return ((result.stdout + result.stderr).strip() or "(no matches)")[:10000]
        except Exception as e:
            return f"Error: grep/findstr failed: {e}"
    except subprocess.TimeoutExpired:
        return "Error: grep timeout"
    except Exception as e:
        return f"Error: {e}"


def run_glob(pattern: str) -> str:
    matches = _glob.glob(pattern, recursive=True)
    if not matches:
        return "(no matches)"
    return "\n".join(sorted(matches)[:200])


def run_revert(path: str) -> str:
    if path not in SNAPSHOTS:
        return f"Error: no snapshot for {path}"
    original_content = SNAPSHOTS.pop(path)
    if original_content is None:
        try:
            os.remove(path)
            return f"reverted: deleted {path} (it was a new file)"
        except Exception as e:
            return f"Error deleting {path}: {e}"
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(original_content)
        return f"reverted: {path}"
    except Exception as e:
        return f"Error reverting {path}: {e}"


async def async_bash(command: str) -> str:
    if any(blocked in command for blocked in _ALWAYS_BLOCK):
        return "Error: dangerous command blocked"
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.getcwd(),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = (stdout.decode() + stderr.decode()).strip()
        return output[:50000] if output else "(no output)"
    except asyncio.TimeoutError:
        return "Error: timeout (120s)"
    except Exception as e:
        return f"Error: {e}"


async def async_read(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_read, path, start_line, end_line)


async def async_write(path: str, content: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_write, path, content)


async def async_grep(pattern: str, path: str = ".", recursive: bool = True) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_grep, pattern, path, recursive)


async def async_glob(pattern: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_glob, pattern)


async def async_revert(path: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_revert, path)
