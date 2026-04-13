import subprocess
import sys
from pathlib import Path


def test_klauso_help():
    src = Path(__file__).resolve().parent.parent / "src"
    r = subprocess.run(
        [sys.executable, "-m", "klauso", "--help"],
        cwd=Path(__file__).resolve().parent.parent,
        env={**__import__("os").environ, "PYTHONPATH": str(src)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0
    assert "workspace" in r.stdout.lower() or "Klauso" in r.stdout or "usage" in r.stdout.lower()
