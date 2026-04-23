"""Tests for pkb completion command."""

from __future__ import annotations

from click.testing import CliRunner

from pkb.cli import cli


def test_completion_bash_outputs_script(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["completion", "bash"])
    assert result.exit_code == 0
    assert "_PKB_COMPLETE" in result.output
    assert "complete -o nosort -F" in result.output


def test_completion_zsh_outputs_script(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["completion", "zsh"])
    assert result.exit_code == 0
    assert "_PKB_COMPLETE" in result.output
    assert "compdef" in result.output


def test_completion_rejects_unsupported_shell(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["completion", "fish"])
    assert result.exit_code != 0
