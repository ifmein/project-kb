"""Tests for pkb task commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from pkb.cli import cli


def test_task_add(db_path: Path, runner: CliRunner, project_name: str) -> None:
    result = runner.invoke(
        cli,
        [
            "task",
            "add",
            "--project",
            project_name,
            "--title",
            "My Task",
            "--priority",
            "P1",
            "--desc",
            "Do stuff",
            "--json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    task = data["task"]
    assert task["title"] == "My Task"
    assert task["priority"] == "P1"
    assert task["status"] == "todo"
    assert task["id"].startswith("task_")


def test_task_list(db_path: Path, runner: CliRunner, project_name: str) -> None:
    runner.invoke(cli, ["task", "add", "--project", project_name, "--title", "t1"])
    runner.invoke(cli, ["task", "add", "--project", project_name, "--title", "t2"])
    result = runner.invoke(cli, ["task", "list", "--project", project_name, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["count"] == 2


def test_task_list_without_project_filter(db_path: Path, runner: CliRunner, project_name: str) -> None:
    runner.invoke(cli, ["task", "add", "--project", project_name, "--title", "t1"])
    runner.invoke(
        cli,
        [
            "project",
            "add",
            "--name",
            "second-project",
            "--json",
        ],
    )
    runner.invoke(cli, ["task", "add", "--project", "second-project", "--title", "t2"])

    result = runner.invoke(cli, ["task", "list", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["count"] == 2


def test_task_list_human_output_includes_project_id(db_path: Path, runner: CliRunner, project_name: str) -> None:
    project_result = runner.invoke(cli, ["project", "show", project_name, "--json"])
    project_id = json.loads(project_result.output)["project"]["id"]

    runner.invoke(cli, ["task", "add", "--project", project_name, "--title", "t1"])
    result = runner.invoke(cli, ["task", "list"])

    assert result.exit_code == 0
    assert "Project" in result.output
    assert project_id in result.output


def test_task_default_invokes_list_json(db_path: Path, runner: CliRunner, project_name: str) -> None:
    runner.invoke(cli, ["task", "add", "--project", project_name, "--title", "t1"])

    result = runner.invoke(cli, ["--json", "task"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["count"] == 1


def test_task_default_invokes_list_human(db_path: Path, runner: CliRunner, project_name: str) -> None:
    runner.invoke(cli, ["task", "add", "--project", project_name, "--title", "t1"])

    result = runner.invoke(cli, ["task"])

    assert result.exit_code == 0
    assert "t1" in result.output


def test_task_list_filter_status(db_path: Path, runner: CliRunner, project_name: str) -> None:
    r = runner.invoke(cli, ["task", "add", "--project", project_name, "--title", "t1", "--json"])
    task_id = json.loads(r.output)["task"]["id"]
    runner.invoke(cli, ["task", "done", task_id])

    result = runner.invoke(cli, ["task", "list", "--project", project_name, "--status", "todo", "--json"])
    data = json.loads(result.output)
    assert data["count"] == 0

    result2 = runner.invoke(cli, ["task", "list", "--project", project_name, "--status", "done", "--json"])
    data2 = json.loads(result2.output)
    assert data2["count"] == 1


def test_task_show(db_path: Path, runner: CliRunner, project_name: str) -> None:
    r = runner.invoke(cli, ["task", "add", "--project", project_name, "--title", "show-me", "--json"])
    task_id = json.loads(r.output)["task"]["id"]
    result = runner.invoke(cli, ["task", "show", task_id, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["task"]["id"] == task_id


def test_task_update(db_path: Path, runner: CliRunner, project_name: str) -> None:
    r = runner.invoke(cli, ["task", "add", "--project", project_name, "--title", "upd-task", "--json"])
    task_id = json.loads(r.output)["task"]["id"]
    result = runner.invoke(cli, ["task", "update", task_id, "--status", "in_progress", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["task"]["status"] == "in_progress"


def test_task_done(db_path: Path, runner: CliRunner, project_name: str) -> None:
    r = runner.invoke(cli, ["task", "add", "--project", project_name, "--title", "finish-me", "--json"])
    task_id = json.loads(r.output)["task"]["id"]
    result = runner.invoke(cli, ["task", "done", task_id, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "done"


def test_task_delete(db_path: Path, runner: CliRunner, project_name: str) -> None:
    r = runner.invoke(cli, ["task", "add", "--project", project_name, "--title", "del-task", "--json"])
    task_id = json.loads(r.output)["task"]["id"]
    result = runner.invoke(cli, ["task", "delete", task_id, "--yes", "--json"])
    assert result.exit_code == 0

    result2 = runner.invoke(cli, ["--json", "task", "show", task_id])
    assert result2.exit_code != 0


def test_task_show_with_task_stats_in_project(db_path: Path, runner: CliRunner, project_name: str) -> None:
    """project show should reflect task counts after adding tasks."""
    r = runner.invoke(cli, ["task", "add", "--project", project_name, "--title", "t1", "--json"])
    task_id = json.loads(r.output)["task"]["id"]
    runner.invoke(cli, ["task", "done", task_id])

    result = runner.invoke(cli, ["project", "show", project_name, "--json"])
    data = json.loads(result.output)
    stats = data["task_stats"]
    assert stats.get("done", 0) == 1
