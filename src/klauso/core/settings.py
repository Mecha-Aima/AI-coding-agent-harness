import os
import shutil
from importlib import resources
from pathlib import Path


def _workspace_root() -> Path:
    return Path(os.environ.get("KLAUSO_WORKSPACE", ".")).resolve()


def _default_config_dir(ws: Path) -> Path:
    return ws / "config"


def _default_skills_dir(ws: Path) -> Path:
    return ws / "skills"


def _bundled_resources() -> Path:
    return Path(str(resources.files("klauso.resources")))


def _ensure_dir_with_defaults(target_dir: Path, names: tuple[str, ...]) -> None:
    """Create target_dir and seed missing YAML files from bundled resources."""
    target_dir.mkdir(parents=True, exist_ok=True)
    bundle = _bundled_resources()
    for name in names:
        dest = target_dir / name
        if dest.exists():
            continue
        src = bundle / name
        if src.is_file():
            try:
                shutil.copyfile(src, dest)
            except OSError:
                pass


def _skills_dir_effective(ws: Path) -> Path:
    env = os.environ.get("KLAUSO_SKILLS_DIR")
    if env:
        return Path(env).expanduser().resolve()
    user = _default_skills_dir(ws)
    if user.is_dir() and any(user.iterdir()):
        return user
    bundled = _bundled_resources() / "skills"
    if bundled.is_dir():
        return bundled
    return user


def _config_dir_effective(ws: Path) -> Path:
    env = os.environ.get("KLAUSO_CONFIG_DIR")
    if env:
        p = Path(env).expanduser().resolve()
        _ensure_dir_with_defaults(p, ("permissions.yaml", "mcp_config.yaml"))
        return p
    user = _default_config_dir(ws)
    _ensure_dir_with_defaults(user, ("permissions.yaml", "mcp_config.yaml"))
    return user


_WORKSPACE = _workspace_root()
CONFIG_DIR: Path = _config_dir_effective(_WORKSPACE)
SKILLS_DIR: Path = _skills_dir_effective(_WORKSPACE)
PACKAGE_ROOT: Path = Path(__file__).resolve().parent.parent

# Sonnet 4.5 — snapshot ID per https://platform.claude.com/docs/en/about-claude/models/overview
DEFAULT_MODEL_ID = "claude-sonnet-4-5-20250929"
MODEL: str = os.environ.get("MODEL_ID", DEFAULT_MODEL_ID)

CACHE_MODE: str = os.environ.get("CACHE_MODE", "anthropic").lower()
ENABLE_TEAMS: bool = os.environ.get("ENABLE_TEAMS", "1").lower() in ("1", "true", "yes")
ENABLE_AUTONOMOUS_WORKERS: bool = os.environ.get("ENABLE_AUTONOMOUS_WORKERS", "0").lower() in ("1", "true", "yes")
HARNESS_DEBUG: bool = os.environ.get("HARNESS_DEBUG", "0").lower() in ("1", "true", "yes")
