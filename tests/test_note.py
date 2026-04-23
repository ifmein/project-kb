"""Tests for pkb note commands."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from pkb.cli import cli


def test_note_add_global(db_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(cli, ["note", "add", "Global memo", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    note = data["note"]
    assert note["content"] == "Global memo"
    assert note["project_id"] is None
    assert note["id"].startswith("note_")


def test_note_add_with_project(db_path: Path, runner: CliRunner, project_name: str) -> None:
    result = runner.invoke(
        cli,
        ["note", "add", "Project memo", "--project", project_name, "--tags", "决策,会议", "--json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    note = data["note"]
    assert note["tags"] == "决策,会议"
    assert note["project_id"] is not None


def test_note_list(db_path: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["note", "add", "note 1"])
    runner.invoke(cli, ["note", "add", "note 2"])
    result = runner.invoke(cli, ["note", "list", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["count"] == 2


def test_note_list_by_project(db_path: Path, runner: CliRunner, project_name: str) -> None:
    runner.invoke(cli, ["note", "add", "global note"])
    runner.invoke(cli, ["note", "add", "proj note", "--project", project_name])
    result = runner.invoke(cli, ["note", "list", "--project", project_name, "--json"])
    data = json.loads(result.output)
    assert data["count"] == 1


def test_note_show(db_path: Path, runner: CliRunner) -> None:
    r = runner.invoke(cli, ["note", "add", "show me", "--json"])
    note_id = json.loads(r.output)["note"]["id"]
    result = runner.invoke(cli, ["note", "show", note_id, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["note"]["content"] == "show me"


def test_note_delete(db_path: Path, runner: CliRunner) -> None:
    r = runner.invoke(cli, ["note", "add", "del me", "--json"])
    note_id = json.loads(r.output)["note"]["id"]
    result = runner.invoke(cli, ["note", "delete", note_id, "--yes", "--json"])
    assert result.exit_code == 0

    result2 = runner.invoke(cli, ["--json", "note", "show", note_id])
    assert result2.exit_code != 0
