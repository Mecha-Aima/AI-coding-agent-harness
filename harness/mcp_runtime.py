"""
MCP runtime — connects stdio MCP servers and routes tool calls.

Key design: ALL context managers (stdio_client + ClientSession) are entered
through a single AsyncExitStack that lives for the full session.  The stack is
closed inside the same coroutine / task that opened it, which satisfies anyio's
cancel-scope ownership rules and avoids the "Attempted to exit cancel scope in
a different task" crash.
"""
import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Set, Tuple

import yaml

from core.settings import CONFIG_DIR

_CONFIG_PATH = CONFIG_DIR / "mcp_config.yaml"

MCP_SESSIONS: Dict[str, Any] = {}
MCP_TOOL_MAP: Dict[str, Tuple[str, str]] = {}

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    print("\033[33mWarning: 'mcp' package not found. Run: pip install mcp\033[0m")


@asynccontextmanager
async def mcp_lifespan() -> AsyncIterator[List[Dict[str, Any]]]:
    """
    Async context manager that owns every MCP connection for the full session.

    Usage (in main coroutine):
        async with mcp_lifespan() as tool_defs:
            ...

    All stdio subprocesses and anyio task groups are entered/exited through a
    single AsyncExitStack, ensuring they are always cleaned up in the same
    asyncio task that created them.
    """
    if not HAS_MCP:
        yield []
        return

    if not _CONFIG_PATH.exists():
        print(f"\033[33m  [MCP] Configuration not found at {_CONFIG_PATH}\033[0m")
        yield []
        return

    try:
        config = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"\033[31m  [MCP] Failed to parse config: {e}\033[0m")
        yield []
        return

    discovered: List[Dict[str, Any]] = []

    async with AsyncExitStack() as stack:
        for srv_cfg in config.get("servers") or []:
            server_name = srv_cfg.get("name", "unnamed_server")
            try:
                if srv_cfg.get("transport", "stdio") != "stdio":
                    print(f"\033[33m  [MCP] {server_name}: transport not supported\033[0m")
                    continue

                params = StdioServerParameters(
                    command=srv_cfg["command"],
                    args=srv_cfg.get("args", []),
                )

                # stack.enter_async_context handles __aenter__ and registers
                # __aexit__ to run when the stack closes — same task, correct order.
                read_stream, write_stream = await stack.enter_async_context(
                    stdio_client(params)
                )
                session: Any = await stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )

                await session.initialize()
                mcp_response = await session.list_tools()
                MCP_SESSIONS[server_name] = session

                print(
                    f"\033[90m  [MCP] {server_name}: Connected "
                    f"({len(mcp_response.tools)} tools)\033[0m"
                )

                for tool in mcp_response.tools:
                    prefixed = f"mcp__{server_name}__{tool.name}"
                    MCP_TOOL_MAP[prefixed] = (server_name, tool.name)
                    discovered.append(
                        {
                            "name": prefixed,
                            "description": f"[{server_name}] {tool.description or tool.name}",
                            "input_schema": tool.inputSchema
                            or {"type": "object", "properties": {}},
                        }
                    )

            except Exception as e:
                print(f"\033[31m  [MCP] Failed to connect to '{server_name}': {e}\033[0m")

        # Yield inside the stack so all CMs stay alive until the caller's block exits.
        try:
            yield discovered
        finally:
            MCP_SESSIONS.clear()
            MCP_TOOL_MAP.clear()
        # AsyncExitStack.__aexit__ runs here, tearing down stdio + sessions cleanly.


async def execute_mcp_tool(prefixed_name: str, arguments: Dict[str, Any]) -> str:
    if prefixed_name not in MCP_TOOL_MAP:
        return f"Error: MCP tool '{prefixed_name}' is not in the registry."
    srv_name, original = MCP_TOOL_MAP[prefixed_name]
    session = MCP_SESSIONS.get(srv_name)
    if not session:
        return f"Error: MCP session for '{srv_name}' is inactive."
    try:
        result = await session.call_tool(original, arguments)
        parts = [item.text for item in (result.content or []) if hasattr(item, "text")]
        return "\n".join(parts)[:50_000] or "(no output received)"
    except Exception as e:
        return f"Error during MCP execution: {e}"


def mcp_tool_name_set() -> Set[str]:
    return set(MCP_TOOL_MAP.keys())
