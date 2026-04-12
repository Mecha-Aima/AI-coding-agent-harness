import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import harness.events as events


@pytest.fixture(autouse=True)
def _reset_event_bus():
    events._hooks_done = False
    events.bus._handlers.clear()
    events.register_default_hooks()
    yield
