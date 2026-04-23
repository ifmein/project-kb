"""Shared pytest fixtures for pkb tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from pkb import db as _db
from pkb.cli import cli


# ---------------------------------------------------------------------------
# DB fixture: isolated temp database
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temp DB and monkeypatch PKB_DB_PATH.

    PKB_SIMPLE_EXT is preserved from the environment so that:
    - Without the env var → unicode61 fallback, pinyin tests are skipped.
    - With the env var → simple tokenizer, pinyin tests run.
    """
    path = tmp_path / "test.db"
    monkeypatch.setenv("PKB_DB_PATH", str(path))
    conn = _db.get_db(path)
    _db.init_db(conn)
    conn.close()
    return path


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# Fixture for tests that need a pre-populated project
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_name(db_path: Path, runner: CliRunner) -> str:
    """Create a 'test-proj' project and return its name."""
    result = runner.invoke(
        cli,
        ["project", "add", "--name", "test-proj", "--desc", "A test project"],
    )
    assert result.exit_code == 0, result.output
    return "test-proj"
