import os
from pathlib import Path

PACKAGE_ROOT: Path = Path(__file__).resolve().parent.parent
CONFIG_DIR: Path = PACKAGE_ROOT / "config"
SKILLS_DIR: Path = PACKAGE_ROOT / "skills"

# Sonnet 4.5 — snapshot ID per https://platform.claude.com/docs/en/about-claude/models/overview
DEFAULT_MODEL_ID = "claude-sonnet-4-5-20250929"
MODEL: str = os.environ.get("MODEL_ID", DEFAULT_MODEL_ID)

CACHE_MODE: str = os.environ.get("CACHE_MODE", "anthropic").lower()
ENABLE_TEAMS: bool = os.environ.get("ENABLE_TEAMS", "1").lower() in ("1", "true", "yes")
ENABLE_AUTONOMOUS_WORKERS: bool = os.environ.get("ENABLE_AUTONOMOUS_WORKERS", "0").lower() in ("1", "true", "yes")
HARNESS_DEBUG: bool = os.environ.get("HARNESS_DEBUG", "0").lower() in ("1", "true", "yes")
