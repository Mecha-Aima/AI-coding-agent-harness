"""MCP config shape (no live stdio)."""

import textwrap
from pathlib import Path

import yaml


def test_sample_mcp_yaml_has_filesystem_and_github():
    p = Path(__file__).resolve().parent.parent / "config" / "mcp_config.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    servers = data.get("servers") or []
    names = {s.get("name") for s in servers}
    assert "filesystem" in names
    assert "github" in names
    for s in servers:
        assert s.get("transport") == "stdio"
        assert "command" in s
