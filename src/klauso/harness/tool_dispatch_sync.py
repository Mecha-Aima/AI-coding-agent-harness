from typing import Any, Callable, Dict, List

from klauso.tools import builtin


def dispatch_tools_sync(response_content: List[Any], dispatch: Dict[str, Callable[..., str]]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for block in response_content:
        if getattr(block, "type", None) != "tool_use":
            continue
        tool_name = block.name
        tool_input = block.input
        tool_use_id = block.id
        handler = dispatch.get(tool_name)
        first_val = str(list(tool_input.values())[0])[:80] if tool_input else ""
        print(f"\033[33m[{tool_name}] {first_val}...\033[0m")
        if handler:
            try:
                output = handler(tool_input)
            except Exception as e:
                output = f"Error during tool execution: {e}"
        else:
            output = f"Error: Unknown tool '{tool_name}'"
        print(str(output)[:300])
        results.append({"type": "tool_result", "tool_use_id": tool_use_id, "content": str(output)})
    return results


def extended_dispatch_map() -> Dict[str, Any]:
    return {
        "bash": lambda inp: builtin.run_bash(inp["command"]),
        "read": lambda inp: builtin.run_read(inp["path"], inp.get("start_line"), inp.get("end_line")),
        "write": lambda inp: builtin.run_write(inp["path"], inp["content"]),
        "grep": lambda inp: builtin.run_grep(inp["pattern"], inp.get("path", "."), inp.get("recursive", True)),
        "glob": lambda inp: builtin.run_glob(inp["pattern"]),
        "revert": lambda inp: builtin.run_revert(inp["path"]),
    }
