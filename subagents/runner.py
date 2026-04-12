from typing import Any, Dict, List

from core.client import client
from core.settings import MODEL
from harness.tool_dispatch_sync import dispatch_tools_sync, extended_dispatch_map
from tools.schemas import EXTENDED_TOOLS


def run_subagent(prompt: str) -> str:
    print(f"\033[35m  [subagent] spawned for: {prompt[:60]}...\033[0m")
    sub_system = (
        f"You are a subagent working on a specific subtask at {__import__('os').getcwd()}. "
        "Complete your task thoroughly. Summarize your result clearly at the end."
    )
    sub_messages: List[Dict[str, Any]] = [{"role": "user", "content": prompt}]
    dispatch = extended_dispatch_map()
    while True:
        response = client.messages.create(
            model=MODEL,
            system=sub_system,
            messages=sub_messages,
            tools=EXTENDED_TOOLS,
            max_tokens=8000,
        )
        sub_messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            break
        results = dispatch_tools_sync(response.content, dispatch)
        sub_messages.append({"role": "user", "content": results})
    final_result = "".join(
        block.text for block in sub_messages[-1]["content"] if hasattr(block, "text")
    )
    print(f"\033[35m  [subagent] done: {final_result[:100]}...\033[0m")
    return final_result


SUBAGENT_TOOL_SCHEMA = {
    "name": "spawn_subagent",
    "description": (
        "Spawn a fresh subagent to handle a subtask in an isolated context. "
        "Use for exploration, risky operations, or tasks that should not pollute the main history."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"prompt": {"type": "string", "description": "Detailed instructions for the subagent."}},
        "required": ["prompt"],
    },
}
