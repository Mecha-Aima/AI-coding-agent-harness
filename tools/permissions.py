import re
from typing import Any, Dict, List, Optional, Tuple

import yaml

from core.settings import CONFIG_DIR

_PERM_CONFIG = CONFIG_DIR / "permissions.yaml"


def permission_check_string(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """
    Build the string matched against permissions.yaml (same intent as s15 / core:
    shell rules apply to the actual command, not a JSON wrapper).
    """
    if not tool_input:
        return tool_name
    if tool_name in ("bash", "bash_background"):
        return str(tool_input.get("command") or "")
    if tool_name in ("read", "write", "revert"):
        return str(tool_input.get("path") or "")
    if tool_name == "grep":
        pat = tool_input.get("pattern", "")
        path = tool_input.get("path", ".")
        rec = tool_input.get("recursive", True)
        return f"grep {pat} {path} recursive={rec}"
    if tool_name == "glob":
        return str(tool_input.get("pattern") or "")
    # First value matches legacy s15 for unknown / extended tools
    return str(next(iter(tool_input.values()), tool_name))


def load_rules() -> Dict[str, List[Dict[str, str]]]:
    try:
        with open(_PERM_CONFIG, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {"always_deny": [], "always_allow": [], "ask_user": []}


def check_permission_sync(tool_name: str, input_str: str, rules: Optional[dict] = None) -> Tuple[bool, str]:
    if rules is None:
        rules = load_rules()
    for rule in rules.get("always_deny", []):
        if re.search(rule["pattern"], input_str, re.IGNORECASE):
            reason = rule.get("reason", "blocked by policy")
            print(f"\033[31m[DENIED] {reason}\033[0m")
            return False, f"Denied: {reason}"
    for rule in rules.get("always_allow", []):
        if re.search(rule["pattern"], input_str, re.IGNORECASE):
            return True, "allowed by policy"
    for rule in rules.get("ask_user", []):
        if re.search(rule["pattern"], input_str, re.IGNORECASE):
            reason = rule.get("reason", "requires user confirmation")
            print(f"\n\033[33m[PERMISSION] {tool_name}: {input_str[:100]}")
            print(f"  Reason: {reason}\033[0m")
            try:
                ans = input("  Allow? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                ans = "n"
            return (ans in ("y", "yes")), "user decision"
    return True, "allowed by default (no rule matched)"


async def check_permission_async(tool_name: str, input_str: str, rules: Optional[dict] = None) -> Tuple[bool, str]:
    import asyncio

    if rules is None:
        rules = load_rules()
    for rule in rules.get("always_deny", []):
        if re.search(rule["pattern"], input_str, re.IGNORECASE):
            reason = rule.get("reason", "blocked by policy")
            print(f"\033[31m[DENIED] {reason}\033[0m")
            return False, f"Denied: {reason}"
    for rule in rules.get("always_allow", []):
        if re.search(rule["pattern"], input_str, re.IGNORECASE):
            return True, "allowed by policy"
    for rule in rules.get("ask_user", []):
        if re.search(rule["pattern"], input_str, re.IGNORECASE):
            reason = rule.get("reason", "requires user confirmation")
            print(f"\n\033[33m[PERMISSION] {tool_name}: {input_str[:100]}")
            print(f"  Reason: {reason}\033[0m")

            def _ask() -> str:
                try:
                    return input("  Allow? [y/N] ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    return "n"

            ans = await asyncio.to_thread(_ask)
            return (ans in ("y", "yes")), "user decision"
    return True, "allowed by default (no rule matched)"
