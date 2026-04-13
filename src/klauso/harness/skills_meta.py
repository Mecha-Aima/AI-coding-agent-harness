import re
from pathlib import Path
from typing import Dict

from klauso.core.settings import SKILLS_DIR


def _unquote_scalar(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def _description_from_frontmatter_block(block: str) -> str | None:
    """Parse description: including YAML folded blocks (description: >-)."""
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.lower().startswith("description:"):
            val = stripped.split(":", 1)[1].strip()
            if val and val not in (">-", ">", "|", "|-", "|+"):
                return _unquote_scalar(val)[:500]
            i += 1
            parts: list[str] = []
            while i < len(lines):
                L = lines[i]
                if L.startswith(("  ", "\t")):
                    parts.append(L.strip())
                    i += 1
                    continue
                if not L.strip() and parts:
                    nxt = i + 1
                    if nxt < len(lines) and lines[nxt].startswith(("  ", "\t")):
                        i += 1
                        continue
                    break
                break
            if parts:
                return " ".join(parts)[:500]
            return None
        i += 1
    return None


def _skill_description(skill_md: Path) -> str:
    """Prefer YAML `description:` inside --- frontmatter; else first plain body line."""
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n", text, re.DOTALL)
    if m:
        block = m.group(1)
        desc = _description_from_frontmatter_block(block)
        if desc:
            return desc
    lines = text.splitlines()
    in_fm = False
    for line in lines:
        stripped = line.strip()
        if stripped == "---":
            in_fm = not in_fm
            continue
        if not in_fm and stripped and not stripped.startswith("#"):
            return stripped[:500]
    return "No description available."


def discover_skills() -> Dict[str, str]:
    skills: Dict[str, str] = {}
    if not SKILLS_DIR.exists():
        return skills
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if skill_dir.is_dir() and skill_md.exists():
            try:
                skills[skill_dir.name] = _skill_description(skill_md)
            except Exception as e:
                skills[skill_dir.name] = f"Error reading metadata: {e}"
    return skills


def run_list_skills() -> str:
    skills = discover_skills()
    if not skills:
        return "(no skills found in skills/ directory)"
    return "\n".join(f"  - {name}: {desc}" for name, desc in skills.items())


def run_load_skill(name: str) -> str:
    skill_path = SKILLS_DIR / name / "SKILL.md"
    if not skill_path.exists():
        return f"Error: skill '{name}' not found. Use list_skills to see valid names."
    try:
        content = skill_path.read_text(encoding="utf-8")
        return f"=== SKILL: {name} ===\n\n{content}\n\n=== END SKILL ==="
    except Exception as e:
        return f"Error loading skill '{name}': {e}"


SKILL_TOOLS_SCHEMA = [
    {
        "name": "list_skills",
        "description": "List all available specialized skills with their descriptions.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "load_skill",
        "description": (
            "Load the full instructions for a skill into your context. "
            "Use this before starting a task requiring specialized domain knowledge."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The exact name of the skill folder to load."}
            },
            "required": ["name"],
        },
    },
]
