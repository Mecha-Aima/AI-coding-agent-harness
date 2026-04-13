import os
from pathlib import Path
from typing import Any, Dict, List

from klauso.core.client import client
from klauso.core.settings import MODEL

COMPRESS_THRESHOLD = 20_000  # characters — compact before context gets unwieldy
KEEP_RECENT = 6
MEMORY_FILE = Path(".agent_memory.md")


def _block_text(block: Any) -> str:
    """Extract a readable string from any content block type."""
    if isinstance(block, str):
        return block
    if isinstance(block, dict):
        t = block.get("type", "")
        if t == "text":
            return block.get("text", "")
        if t == "tool_use":
            import json
            inp = block.get("input", {})
            return f"<tool_use name={block.get('name','?')} input={json.dumps(inp, default=str)[:300]}>"
        if t == "tool_result":
            content = block.get("content", "")
            if isinstance(content, list):
                return " ".join(_block_text(b) for b in content)
            return str(content)
        # fallback: stringify whatever is there
        return str(block.get("text") or block.get("content") or "")
    # SDK objects
    if hasattr(block, "type"):
        btype = block.type
        if btype == "text":
            return getattr(block, "text", "") or ""
        if btype == "tool_use":
            import json
            inp = getattr(block, "input", {})
            return f"<tool_use name={block.name} input={json.dumps(inp, default=str)[:300]}>"
        if btype == "tool_result":
            content = getattr(block, "content", "")
            if isinstance(content, list):
                return " ".join(_block_text(b) for b in content)
            return str(content)
    return str(block)


def _message_text(msg: Dict[str, Any]) -> str:
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(_block_text(b) for b in content)
    return str(content)


def estimate_size(messages: List[Dict[str, Any]]) -> int:
    return sum(len(_message_text(m)) for m in messages)


def _summarize(messages: List[Dict[str, Any]]) -> str:
    text_to_summarize = "\n\n".join(
        f"[{m['role']}]: {_message_text(m)}" for m in messages
    )
    if not text_to_summarize.strip():
        return "(no prior history)"
    response = client.messages.create(
        model=MODEL,
        system=(
            "You are a context compressor. Summarize the provided conversation history "
            "concisely. Retain critical technical decisions, file paths, code changes, and pending tasks."
        ),
        messages=[
            {
                "role": "user",
                "content": f"Summarize this conversation history:\n\n{text_to_summarize[:20_000]}",
            }
        ],
        max_tokens=2000,
    )
    return "".join(block.text for block in response.content if hasattr(block, "text"))


def maybe_compact(messages: List[Dict[str, Any]]) -> None:
    if estimate_size(messages) < COMPRESS_THRESHOLD:
        return
    old_prefix = messages[:-KEEP_RECENT]
    if not old_prefix:
        return
    recent = messages[-KEEP_RECENT:]
    summary = _summarize(old_prefix)
    existing = MEMORY_FILE.read_text(encoding="utf-8") if MEMORY_FILE.exists() else ""
    MEMORY_FILE.write_text(
        existing + f"\n\n## Session {os.path.basename(os.getcwd())}\n{summary}\n",
        encoding="utf-8",
    )
    messages.clear()
    messages.extend(
        [
            {
                "role": "user",
                "content": f"[COMPRESSED MEMORY — see {MEMORY_FILE}]\n{summary}",
            },
            {
                "role": "assistant",
                "content": "Understood. Continuing with recent context below.",
            },
            *recent,
        ]
    )
    print(f"\033[90m  [memory] compressed older turns → {MEMORY_FILE}\033[0m")
