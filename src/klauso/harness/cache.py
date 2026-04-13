import copy
import os
from typing import Any, Dict, List

from klauso.tools.schemas import EXTENDED_TOOLS


class CacheStats:
    def __init__(self) -> None:
        self.created = 0
        self.read = 0
        self.uncached = 0
        self.calls = 0

    def record(self, usage: Any) -> None:
        self.calls += 1
        self.created += getattr(usage, "cache_creation_input_tokens", 0) or 0
        self.read += getattr(usage, "cache_read_input_tokens", 0) or 0
        self.uncached += getattr(usage, "input_tokens", 0) or 0

    def show_turn(self, usage: Any) -> None:
        created = getattr(usage, "cache_creation_input_tokens", 0) or 0
        read = getattr(usage, "cache_read_input_tokens", 0) or 0
        if created > 0:
            print(f"\033[90m  [cache] MISS → {created} tokens written to cache\033[0m")
        elif read > 0:
            saved = int(read * 0.9)
            print(f"\033[90m  [cache] HIT  → {read} tokens read (saved ≈{saved} tokens)\033[0m")

    def summary(self) -> None:
        if self.calls > 0:
            total_saved = int(self.read * 0.9)
            print(
                f"\n\033[90m  [cache total] turns={self.calls} | written={self.created} "
                f"| hits={self.read} | estimated savings={total_saved} tokens\033[0m"
            )


def build_cached_system(base_text: str) -> List[Dict[str, Any]]:
    return [
        {
            "type": "text",
            "text": base_text,
            "cache_control": {"type": "ephemeral"},
        }
    ]


def apply_cache_to_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cached = copy.deepcopy(tools)
    if cached:
        cached[-1]["cache_control"] = {"type": "ephemeral"}
    return cached


def default_cacheable_system_text() -> str:
    return (
        f"You are a coding agent at {os.getcwd()}. "
        "Use tools to solve tasks. Be concise.\n\n"
        "If you receive a message starting with [INTERRUPT], stop, summarize progress, and wait.\n"
        "Use list_skills / load_skill for domain guides. Use todo_* and task_* for planning.\n"
        "Tools: bash, read, write, grep, glob, revert, bash_background, spawn_subagent, teammates, MCP (mcp__*)."
    )
