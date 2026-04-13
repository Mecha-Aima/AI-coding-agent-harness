import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

_ws = Path(os.environ.get("KLAUSO_WORKSPACE", ".")).resolve()
load_dotenv(_ws / ".env", override=True)
load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
