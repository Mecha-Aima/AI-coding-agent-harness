"""Default permissions YAML structure."""

from pathlib import Path

import yaml


def test_repo_permissions_has_deny_allow_ask_order():
    p = Path(__file__).resolve().parent.parent / "config" / "permissions.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert "always_deny" in data
    assert "always_allow" in data
    assert "ask_user" in data
    deny = " ".join(r["pattern"] for r in data["always_deny"])
    assert "sudo" in deny.lower() or any("sudo" in r["pattern"] for r in data["always_deny"])
    ask = " ".join(r["pattern"] for r in data["ask_user"])
    assert "git" in ask.lower()
