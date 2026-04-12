from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List

_LOG_FILE = ".agent_events.log"


class EventBus:
    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable[..., Any]]] = defaultdict(list)

    def on(self, event: str, handler: Callable[..., Any]) -> "EventBus":
        self._handlers[event].append(handler)
        return self

    def emit(self, event: str, **payload: Any) -> List[Any]:
        results: List[Any] = []
        for handler in self._handlers[event]:
            try:
                result = handler(event=event, **payload)
                if result is not None:
                    results.append(result)
            except Exception as e:
                print(f"\033[31m[EventBus] Hook error on '{event}': {e}\033[0m")
        return results


bus = EventBus()


def hook_logger(event: str, **payload: Any) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tool_name = payload.get("tool", "N/A")
    tag = "[tool]"
    if isinstance(tool_name, str) and tool_name.startswith("mcp__"):
        tag = "[mcp]"
    elif event == "tool_error":
        tag = "[err]"
    log_line = f"[{timestamp}] {tag} EVENT={event} TOOL={tool_name}"
    with open(_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")


def hook_permission_denied(event: str, **payload: Any) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tool_name = payload.get("tool", "N/A")
    reason = str(payload.get("reason", ""))[:500]
    line = f"[{timestamp}] [perm] EVENT={event} TOOL={tool_name} REASON={reason}"
    with open(_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def hook_stats(event: str, **payload: Any) -> None:
    if not hasattr(hook_stats, "_counts"):
        hook_stats._counts = defaultdict(int)
    if event == "session_start":
        hook_stats._counts.clear()
    elif event == "post_tool_use":
        tool = payload.get("tool", "unknown")
        hook_stats._counts[tool] += 1
    elif event == "session_end":
        if hook_stats._counts:
            print(f"\033[90m  [stats] Tool Usage: {dict(hook_stats._counts)}\033[0m")


def hook_timer(event: str, **payload: Any) -> None:
    if not hasattr(hook_timer, "_start_times"):
        hook_timer._start_times = {}
    if event == "pre_tool_use":
        hook_timer._start_times[payload.get("tool")] = datetime.now()
    elif event == "post_tool_use":
        tool_name = payload.get("tool")
        start_time = hook_timer._start_times.pop(tool_name, None)
        if start_time:
            duration = (datetime.now() - start_time).total_seconds()
            if duration > 5.0:
                print(f"\033[90m  [timer] Warning: '{tool_name}' was slow ({duration:.1f}s)\033[0m")


_hooks_done = False


def register_default_hooks() -> None:
    global _hooks_done
    if _hooks_done:
        return
    bus.on("pre_tool_use", hook_logger).on("post_tool_use", hook_logger).on("tool_error", hook_logger)
    bus.on("permission_denied", hook_permission_denied)
    bus.on("session_start", hook_stats).on("post_tool_use", hook_stats).on("session_end", hook_stats)
    bus.on("pre_tool_use", hook_timer).on("post_tool_use", hook_timer)
    _hooks_done = True
