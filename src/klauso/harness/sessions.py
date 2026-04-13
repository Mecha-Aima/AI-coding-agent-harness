import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from klauso.utils.serialization import serialize_messages

SESSIONS_DIR = Path(".sessions")
SESSIONS_DIR.mkdir(exist_ok=True)


def create_new_session() -> Dict[str, Any]:
    return {
        "id": uuid.uuid4().hex[:8],
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
        "title": "New Session",
        "messages": [],
    }


def save_session(session_data: Dict[str, Any]) -> None:
    session_data["updated"] = datetime.now().isoformat()
    file_path = SESSIONS_DIR / f"{session_data['id']}.json"
    json_ready = {**session_data, "messages": serialize_messages(session_data["messages"])}
    file_path.write_text(json.dumps(json_ready, indent=2), encoding="utf-8")


def load_session(session_id: str) -> Optional[Dict[str, Any]]:
    file_path = SESSIONS_DIR / f"{session_id}.json"
    if not file_path.exists():
        return None
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"\033[31m  [error] Failed to load session {session_id}: {e}\033[0m")
        return None


def list_all_sessions() -> List[Dict[str, Any]]:
    sessions: List[Dict[str, Any]] = []
    files = sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files:
        try:
            sessions.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    return sessions


def print_sessions_table() -> None:
    sessions = list_all_sessions()
    if not sessions:
        print("  (No saved sessions found in .sessions/)")
        return
    print("\n  \033[4mID        LAST UPDATED         TITLE (MESSAGES)\033[0m")
    for s in sessions:
        msg_count = len(s.get("messages", []))
        print(
            f"  \033[36m{s['id']}\033[0m  {s['updated'][:19]}  {s['title'][:40]:40} \033[90m({msg_count} msgs)\033[0m"
        )
    print()
