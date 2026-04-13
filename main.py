"""Run from repo: ``python main.py``. Installed: ``klauso`` or ``python -m klauso``."""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from klauso.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
