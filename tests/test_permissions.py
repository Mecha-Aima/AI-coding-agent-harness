import pytest

from tools.permissions import check_permission_sync, permission_check_string


def test_permission_check_string_bash_uses_command_not_json():
    """YAML rules anchor on the shell command (s15); must not use json.dumps(tool_input)."""
    s = permission_check_string("bash", {"command": "rm tmp/foo.txt"})
    assert s == "rm tmp/foo.txt"
    assert s.startswith("rm ")


def test_permission_check_string_read_uses_path():
    s = permission_check_string("read", {"path": ".env"})
    assert ".env" in s


def test_always_deny_blocks_rm_rf_root():
    rules = {"always_deny": [{"pattern": r"rm\s+-rf\s+/", "reason": "no"}]}
    ok, _ = check_permission_sync("bash", "rm -rf /", rules)
    assert ok is False


def test_default_allow_when_no_rule():
    rules = {"always_deny": [], "always_allow": [], "ask_user": []}
    ok, _ = check_permission_sync("bash", "echo hi", rules)
    assert ok is True
