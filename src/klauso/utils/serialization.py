from typing import Any, Dict, List

# Fields the Anthropic Messages API accepts per content block type.
# Any field NOT in these sets is an SDK-internal detail that must be stripped
# before sending the message list back to the API (e.g. `citations`,
# `parsed_output`, `caller` that the SDK adds on model_dump()).
_TEXT_FIELDS = {"type", "text"}
_TOOL_USE_FIELDS = {"type", "id", "name", "input"}
_TOOL_RESULT_FIELDS = {"type", "tool_use_id", "content", "is_error"}
_IMAGE_FIELDS = {"type", "source"}
_DOCUMENT_FIELDS = {"type", "source", "title", "context", "citations"}


def _clean_block(block: Any) -> Dict[str, Any]:
    """Convert an SDK content block to a plain dict with only API-legal fields."""
    if isinstance(block, dict):
        raw = block
    elif hasattr(block, "model_dump"):
        raw = block.model_dump()
    elif hasattr(block, "__dict__"):
        raw = block.__dict__
    else:
        return block  # type: ignore[return-value]

    block_type = raw.get("type", "")
    if block_type == "text":
        return {k: v for k, v in raw.items() if k in _TEXT_FIELDS}
    if block_type == "tool_use":
        return {k: v for k, v in raw.items() if k in _TOOL_USE_FIELDS}
    if block_type == "tool_result":
        return {k: v for k, v in raw.items() if k in _TOOL_RESULT_FIELDS}
    if block_type == "image":
        return {k: v for k, v in raw.items() if k in _IMAGE_FIELDS}
    if block_type == "document":
        return {k: v for k, v in raw.items() if k in _DOCUMENT_FIELDS}
    # Unknown block type — pass through as-is but still as a plain dict.
    return dict(raw)


def serialize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    serialized: List[Dict[str, Any]] = []
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            content = [_clean_block(b) for b in content]
        serialized.append({"role": msg["role"], "content": content})
    return serialized
