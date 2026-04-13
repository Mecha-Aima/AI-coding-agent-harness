import json
import threading
from pathlib import Path

import pytest

import klauso.harness.teams as teams


@pytest.fixture
def mailbox_dir(tmp_path, monkeypatch):
    d = tmp_path / ".mailboxes"
    monkeypatch.setattr(teams, "MAILBOX_DIR", d)
    return d


def test_concurrent_mailbox_writes_are_valid_jsonl(mailbox_dir):
    def writer(n: int) -> None:
        for i in range(30):
            teams._send_message("explorer", "stress", f"msg-{n}-{i}", "request")

    threads = [threading.Thread(target=writer, args=(k,)) for k in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    path: Path = teams._mailbox_path("explorer")
    assert path.exists()
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 6 * 30
    for ln in lines:
        obj = json.loads(ln)
        assert {"from", "type", "body", "timestamp"} <= set(obj.keys())
