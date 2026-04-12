from types import SimpleNamespace

from utils.serialization import serialize_messages


def test_serialize_messages_dict_content_roundtrip():
    messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": [{"type": "text", "text": "hi"}]},
    ]
    out = serialize_messages(messages)
    assert out[0]["content"] == "hello"
    assert out[1]["content"] == [{"type": "text", "text": "hi"}]


def test_serialize_messages_model_dump_blocks():
    block = SimpleNamespace(model_dump=lambda: {"type": "tool_use", "id": "x", "name": "read", "input": {}})
    messages = [{"role": "assistant", "content": [block]}]
    out = serialize_messages(messages)
    assert out[0]["content"][0]["name"] == "read"
