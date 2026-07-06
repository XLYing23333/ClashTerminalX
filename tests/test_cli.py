from pathlib import Path

import pytest

from clashtx.cli import main


def test_help_command(capsys):
    assert main(["help"]) == 0
    output = capsys.readouterr().out
    assert "update-core" not in output
    assert "enable" not in output
    assert "start" in output
    assert "source" in output
    assert "No command starts the Textual TUI" in output


def test_unknown_command(capsys):
    assert main(["nope"]) == 2
    output = capsys.readouterr().out
    assert "Unknown command" in output


def test_source_command_missing_env(tmp_path, monkeypatch, capsys):
    missing = tmp_path / "proxy.env"

    class ProxyStub:
        env_file = missing

    monkeypatch.setattr("clashtx.system.proxy.ProxyManager", lambda store=None: ProxyStub())

    assert main(["source"]) == 1
    output = capsys.readouterr().out
    assert "Proxy env not found" in output


def test_source_command_shows_usage(tmp_path, monkeypatch, capsys):
    env_file = tmp_path / "proxy.env"
    env_file.write_text("export http_proxy=http://127.0.0.1:7897\n", encoding="utf-8")

    class ProxyStub:
        pass

    ProxyStub.env_file = env_file

    monkeypatch.setattr("clashtx.system.proxy.ProxyManager", lambda store=None: ProxyStub())

    assert main(["source"]) == 0
    output = capsys.readouterr().out
    assert str(env_file) in output
    assert "source ./clashtx.sh source" in output
