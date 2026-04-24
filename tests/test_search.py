"""Tests for pkb search command."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from pkb.cli import cli


# ---------------------------------------------------------------------------
# Basic FTS (unicode61) search — works without simple ext
# ---------------------------------------------------------------------------


def test_search_note_by_keyword(db_path: Path, runner: CliRunner, project_name: str) -> None:
    runner.invoke(
        cli,
        ["note", "add", "今天讨论了 ntfy 推送方案", "--project", project_name, "--tags", "决策"],
    )
    result = runner.invoke(cli, ["search", "ntfy", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["count"] >= 1
    assert any(r["type"] == "note" for r in data["results"])


def test_search_task_by_keyword(db_path: Path, runner: CliRunner, project_name: str) -> None:
    runner.invoke(
        cli,
        ["task", "add", "--project", project_name, "--title", "实现 ntfy 消息推送"],
    )
    result = runner.invoke(cli, ["search", "ntfy", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["count"] >= 1
    assert any(r["type"] == "task" for r in data["results"])


def test_search_no_results(db_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(cli, ["search", "xyzzy_nonexistent_token_abc123", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["count"] == 0


def test_search_type_filter_note(db_path: Path, runner: CliRunner, project_name: str) -> None:
    runner.invoke(cli, ["note", "add", "keyword here", "--project", project_name])
    runner.invoke(cli, ["task", "add", "--project", project_name, "--title", "keyword here"])
    result = runner.invoke(cli, ["search", "keyword", "--type", "note", "--json"])
    data = json.loads(result.output)
    assert all(r["type"] == "note" for r in data["results"])


def test_search_type_filter_task(db_path: Path, runner: CliRunner, project_name: str) -> None:
    runner.invoke(cli, ["note", "add", "keyword here", "--project", project_name])
    runner.invoke(cli, ["task", "add", "--project", project_name, "--title", "keyword here"])
    result = runner.invoke(cli, ["search", "keyword", "--type", "task", "--json"])
    data = json.loads(result.output)
    assert all(r["type"] == "task" for r in data["results"])


def test_search_project_filter(db_path: Path, runner: CliRunner, project_name: str) -> None:
    # Add a second project with a note using the same keyword
    runner.invoke(cli, ["project", "add", "--name", "other-proj"])
    runner.invoke(cli, ["note", "add", "uniquekeyword", "--project", project_name])
    runner.invoke(cli, ["note", "add", "uniquekeyword", "--project", "other-proj"])

    result = runner.invoke(cli, ["search", "uniquekeyword", "--project", project_name, "--json"])
    data = json.loads(result.output)
    assert data["count"] == 1
    assert data["results"][0]["project"] == project_name


def test_search_result_schema(db_path: Path, runner: CliRunner, project_name: str) -> None:
    """Verify the JSON schema matches PRD spec."""
    runner.invoke(cli, ["note", "add", "schema test", "--project", project_name])
    result = runner.invoke(cli, ["search", "schema", "--json"])
    data = json.loads(result.output)
    assert "success" in data
    assert "query" in data
    assert "results" in data
    assert "count" in data
    # No rank field exposed
    for r in data["results"]:
        assert "_rank" not in r
        assert "rank" not in r


def test_search_project_result_includes_local_path(db_path: Path, runner: CliRunner) -> None:
    local_path = "/tmp/pkb-search-proj"
    project_name = "pathproj"
    runner.invoke(
        cli,
        ["project", "add", "--name", project_name, "--path", local_path],
    )

    result = runner.invoke(cli, ["search", project_name, "--type", "project", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["count"] >= 1

    project_results = [r for r in data["results"] if r["type"] == "project" and r["name"] == project_name]
    assert project_results
    assert project_results[0]["local_path"] == local_path


# ---------------------------------------------------------------------------
# Pinyin search — only with simple tokenizer
# ---------------------------------------------------------------------------


def _has_simple_ext() -> bool:
    ext = os.environ.get("PKB_SIMPLE_EXT", "")
    return bool(ext)


@pytest.mark.skipif(not _has_simple_ext(), reason="simple tokenizer not available")
def test_search_pinyin(db_path: Path, runner: CliRunner, project_name: str) -> None:
    runner.invoke(
        cli,
        ["note", "add", "今天做了关于决策的讨论", "--project", project_name],
    )
    result = runner.invoke(cli, ["search", "jue ce", "--json"])
    data = json.loads(result.output)
    assert data["count"] >= 1
