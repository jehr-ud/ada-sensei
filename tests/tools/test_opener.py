"""Best-effort OS opener for the exam report (RQ-EXM-049)."""

from __future__ import annotations

import ada_sensei.tools.opener as opener


def test_open_path_missing_file_returns_false(tmp_path):
    assert opener.open_path(tmp_path / "nope.pdf") is False


def test_open_path_launches_platform_opener(tmp_path, monkeypatch):
    target = tmp_path / "report.pdf"
    target.write_bytes(b"%PDF-1.4")
    calls: list[list[str]] = []

    def fake_popen(cmd, **_kwargs):
        calls.append(list(cmd))
        return object()

    monkeypatch.setattr(opener.subprocess, "Popen", fake_popen)
    assert opener.open_path(target) is True
    assert calls and calls[0][-1] == str(target)


def test_open_path_swallows_launch_errors(tmp_path, monkeypatch):
    target = tmp_path / "report.pdf"
    target.write_bytes(b"%PDF-1.4")

    def boom(_cmd, **_kwargs):
        raise OSError("no opener available")

    monkeypatch.setattr(opener.subprocess, "Popen", boom)
    assert opener.open_path(target) is False
