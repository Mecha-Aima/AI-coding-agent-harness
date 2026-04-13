from klauso.harness.loop import build_async_dispatch, build_merged_tool_definitions


def test_merged_tools_include_core_names():
    tools = build_merged_tool_definitions([])
    names = {t["name"] for t in tools}
    assert "bash" in names
    assert "spawn_subagent" in names
    assert "todo_write" in names
    assert "task_create" in names


def test_async_dispatch_has_handlers():
    d = build_async_dispatch()
    assert "bash" in d
    assert "load_skill" in d
