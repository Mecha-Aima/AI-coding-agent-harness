import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from klauso.harness.events import bus
from klauso.harness.loop import dispatch_one_tool


def test_pre_tool_use_hook_blocks_execution():
    def blocker(event: str, **payload):
        if event == "pre_tool_use" and payload.get("tool") == "read":
            return {"block": True}

    bus.on("pre_tool_use", blocker)
    block = SimpleNamespace(id="tu1", name="read", input={"path": "x"})

    async def _run():
        tid, out = await dispatch_one_tool(block, set(), {}, {})
        assert tid == "tu1"
        assert "blocked" in out.lower()

    asyncio.run(_run())


def test_permission_denied_emits_bus():
    seen: list[tuple[str, str | None]] = []

    def on_perm(event: str, **payload):
        seen.append((event, payload.get("tool")))

    bus.on("permission_denied", on_perm)
    rules = {"always_deny": [{"pattern": ".*", "reason": "nope"}], "always_allow": [], "ask_user": []}
    block = SimpleNamespace(id="tu2", name="bash", input={"command": "echo hi"})

    async def _run():
        tid, out = await dispatch_one_tool(block, set(), {}, rules)
        assert tid == "tu2"
        assert "Denied" in out
        assert any(e == "permission_denied" and t == "bash" for e, t in seen)

    asyncio.run(_run())


def test_parallel_dispatch_results_all_ids():
    rules = {"always_deny": [], "always_allow": [], "ask_user": []}
    blocks = [
        SimpleNamespace(id="a", name="read", input={"path": __file__, "start_line": 1, "end_line": 2}),
        SimpleNamespace(id="b", name="glob", input={"pattern": "*.py"}),
    ]
    dispatch = {"read": AsyncMock(return_value="ok-read"), "glob": AsyncMock(return_value="ok-glob")}

    async def _run():
        with patch("klauso.harness.loop.check_permission_async", new_callable=AsyncMock) as perm:
            perm.return_value = (True, "")
            results = await asyncio.gather(
                *[dispatch_one_tool(b, set(), dispatch, rules) for b in blocks]
            )
        by_id = dict(results)
        assert set(by_id) == {"a", "b"}
        assert "ok-read" in by_id["a"]
        assert "ok-glob" in by_id["b"]

    asyncio.run(_run())
