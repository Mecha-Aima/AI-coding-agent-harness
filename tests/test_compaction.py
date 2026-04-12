import memory.compaction as compaction


def test_maybe_compact_shrinks_history(monkeypatch, tmp_path):
    monkeypatch.setattr(compaction, "COMPRESS_THRESHOLD", 100)
    monkeypatch.setattr(compaction, "KEEP_RECENT", 2)
    monkeypatch.setattr(compaction, "MEMORY_FILE", tmp_path / ".agent_memory.md")
    monkeypatch.setattr(compaction, "_summarize", lambda _msgs: "SUMMARY")

    messages = [
        {"role": "user", "content": "x" * 80},
        {"role": "assistant", "content": "y" * 80},
        {"role": "user", "content": "z" * 80},
        {"role": "assistant", "content": "w" * 80},
    ]
    compaction.maybe_compact(messages)

    assert len(messages) == 4  # user summary + assistant ack + 2 recent
    assert "SUMMARY" in messages[0]["content"]
    assert compaction.MEMORY_FILE.exists()
