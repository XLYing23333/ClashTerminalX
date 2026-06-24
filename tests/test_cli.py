from clashtx.cli import main


def test_help_command(capsys):
    assert main(["help"]) == 0
    output = capsys.readouterr().out
    assert "update-core" not in output
    assert "enable" not in output
    assert "start" in output
    assert "No command starts the Textual TUI" in output


def test_unknown_command(capsys):
    assert main(["nope"]) == 2
    output = capsys.readouterr().out
    assert "Unknown command" in output
