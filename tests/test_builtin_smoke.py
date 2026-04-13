"""Smoke tests for klauso.tools.builtin (no API calls)."""

from pathlib import Path

from klauso.tools import builtin


def test_run_read_numbered_lines(tmp_path: Path):
    p = tmp_path / "f.txt"
    p.write_text("a\nb\nc\n", encoding="utf-8")
    out = builtin.run_read(str(p), 1, 2)
    assert "a" in out and "b" in out


def test_run_write_and_revert(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p = tmp_path / "w.txt"
    builtin.run_write(str(p), "v1")
    assert p.read_text() == "v1"
    builtin.run_write(str(p), "v2")
    assert p.read_text() == "v2"
    r = builtin.run_revert(str(p))
    assert "reverted" in r.lower()
    assert p.read_text() == "v1"


def test_run_glob(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    out = builtin.run_glob("*.py")
    assert "a.py" in out


def test_run_bash_echo(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = builtin.run_bash("echo hello")
    assert "hello" in out


def test_run_bash_blocks_sudo(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = builtin.run_bash("sudo ls")
    assert "blocked" in out.lower() or "Error" in out
