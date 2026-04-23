"""Tests for pkb project commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from pkb.cli import cli


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_project_list_empty(db_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(cli, ["project", "list", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["projects"] == []


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


def test_project_add(db_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        ["project", "add", "--name", "my-proj", "--desc", "hello", "--json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    proj = data["project"]
    assert proj["name"] == "my-proj"
    assert proj["description"] == "hello"
    assert proj["status"] == "active"
    assert proj["id"].startswith("proj_")


def test_project_add_appears_in_list(db_path: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["project", "add", "--name", "proj-a", "--json"])
    result = runner.invoke(cli, ["project", "list", "--json"])
    data = json.loads(result.output)
    names = [p["name"] for p in data["projects"]]
    assert "proj-a" in names


def test_project_add_duplicate_fails(db_path: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["project", "add", "--name", "dup"])
    result = runner.invoke(cli, ["project", "add", "--name", "dup"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------


def test_project_show_by_name(db_path: Path, runner: CliRunner, project_name: str) -> None:
    result = runner.invoke(cli, ["project", "show", project_name, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["project"]["name"] == project_name
    assert "task_stats" in data


def test_project_show_missing(db_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--json", "project", "show", "nonexistent"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def test_project_update(db_path: Path, runner: CliRunner, project_name: str) -> None:
    result = runner.invoke(
        cli,
        ["project", "update", project_name, "--status", "paused", "--json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["project"]["status"] == "paused"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_project_delete(db_path: Path, runner: CliRunner, project_name: str) -> None:
    result = runner.invoke(cli, ["project", "delete", project_name, "--yes", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True

    # Verify it's gone
    result2 = runner.invoke(cli, ["--json", "project", "show", project_name])
    assert result2.exit_code != 0


def test_project_delete_cascades_tasks(db_path: Path, runner: CliRunner, project_name: str) -> None:
    # Add a task
    runner.invoke(
        cli,
        ["task", "add", "--project", project_name, "--title", "t1"],
    )
    # Delete project
    runner.invoke(cli, ["project", "delete", project_name, "--yes"])
    # Re-create same-name project — task should be gone
    runner.invoke(cli, ["project", "add", "--name", project_name])
    result = runner.invoke(cli, ["task", "list", "--project", project_name, "--json"])
    data = json.loads(result.output)
    assert data["count"] == 0
