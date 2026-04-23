"""Tests for CLI commands."""

import json
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli import main
from db import Database


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def temp_db(monkeypatch):
    """Create a temporary database and patch Database to use it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        monkeypatch.setattr("cli.Database", lambda: Database(db_path))
        yield db_path


class TestProjectCLI:
    """Test project CLI commands."""

    def test_project_add(self, runner, temp_db):
        """Test adding a project."""
        result = runner.invoke(main, ["project", "add", "--name", "test-project", "--desc", "Test"])
        assert result.exit_code == 0
        assert "Project created" in result.output

    def test_project_add_json(self, runner, temp_db):
        """Test adding a project with JSON output."""
        result = runner.invoke(main, ["project", "add", "--name", "test-project", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["project"]["name"] == "test-project"

    def test_project_list(self, runner, temp_db):
        """Test listing projects."""
        # Add a project first
        runner.invoke(main, ["project", "add", "--name", "test-project"])
        
        result = runner.invoke(main, ["project", "list"])
        assert result.exit_code == 0
        assert "test-project" in result.output

    def test_project_list_json(self, runner, temp_db):
        """Test listing projects with JSON output."""
        runner.invoke(main, ["project", "add", "--name", "test-project"])
        
        result = runner.invoke(main, ["project", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert len(data["projects"]) == 1

    def test_project_show(self, runner, temp_db):
        """Test showing project details."""
        # Add a project
        runner.invoke(main, ["project", "add", "--name", "test-project"])
        
        # Get the project ID from list
        result = runner.invoke(main, ["project", "list", "--json"])
        data = json.loads(result.output)
        project_id = data["projects"][0]["id"]
        
        # Show project
        result = runner.invoke(main, ["project", "show", project_id])
        assert result.exit_code == 0
        assert "test-project" in result.output

    def test_project_update(self, runner, temp_db):
        """Test updating a project."""
        # Add a project
        runner.invoke(main, ["project", "add", "--name", "test-project"])
        
        # Get project ID
        result = runner.invoke(main, ["project", "list", "--json"])
        data = json.loads(result.output)
        project_id = data["projects"][0]["id"]
        
        # Update project
        result = runner.invoke(main, ["project", "update", project_id, "--status", "paused"])
        assert result.exit_code == 0
        assert "Project updated" in result.output

    def test_project_delete(self, runner, temp_db):
        """Test deleting a project."""
        # Add a project
        runner.invoke(main, ["project", "add", "--name", "test-project"])
        
        # Get project ID
        result = runner.invoke(main, ["project", "list", "--json"])
        data = json.loads(result.output)
        project_id = data["projects"][0]["id"]
        
        # Delete project
        result = runner.invoke(main, ["project", "delete", project_id])
        assert result.exit_code == 0
        assert "Project deleted" in result.output


class TestTaskCLI:
    """Test task CLI commands."""

    def test_task_add(self, runner, temp_db):
        """Test adding a task."""
        # Add a project first
        runner.invoke(main, ["project", "add", "--name", "test-project"])
        
        # Get project ID
        result = runner.invoke(main, ["project", "list", "--json"])
        data = json.loads(result.output)
        project_id = data["projects"][0]["id"]
        
        # Add task
        result = runner.invoke(main, ["task", "add", "--project", project_id, "--title", "Test task"])
        assert result.exit_code == 0
        assert "Task created" in result.output

    def test_task_list(self, runner, temp_db):
        """Test listing tasks."""
        # Add project and task
        runner.invoke(main, ["project", "add", "--name", "test-project"])
        result = runner.invoke(main, ["project", "list", "--json"])
        project_id = json.loads(result.output)["projects"][0]["id"]
        
        runner.invoke(main, ["task", "add", "--project", project_id, "--title", "Test task"])
        
        # List tasks
        result = runner.invoke(main, ["task", "list", "--project", project_id])
        assert result.exit_code == 0
        assert "Test task" in result.output

    def test_task_done(self, runner, temp_db):
        """Test marking task as done."""
        # Add project and task
        runner.invoke(main, ["project", "add", "--name", "test-project"])
        result = runner.invoke(main, ["project", "list", "--json"])
        project_id = json.loads(result.output)["projects"][0]["id"]
        
        runner.invoke(main, ["task", "add", "--project", project_id, "--title", "Test task"])
        
        # Get task ID
        result = runner.invoke(main, ["task", "list", "--project", project_id, "--json"])
        task_id = json.loads(result.output)["tasks"][0]["id"]
        
        # Mark as done
        result = runner.invoke(main, ["task", "done", task_id])
        assert result.exit_code == 0
        assert "Task marked as done" in result.output


class TestNoteCLI:
    """Test note CLI commands."""

    def test_note_add(self, runner, temp_db):
        """Test adding a note."""
        # Add a project first
        runner.invoke(main, ["project", "add", "--name", "test-project"])
        
        # Get project ID
        result = runner.invoke(main, ["project", "list", "--json"])
        data = json.loads(result.output)
        project_id = data["projects"][0]["id"]
        
        # Add note
        result = runner.invoke(main, ["note", "add", "Test note content", "--project", project_id])
        assert result.exit_code == 0
        assert "Note created" in result.output

    def test_note_add_global(self, runner, temp_db):
        """Test adding a global note."""
        result = runner.invoke(main, ["note", "add", "Global note"])
        assert result.exit_code == 0
        assert "Note created" in result.output

    def test_note_list(self, runner, temp_db):
        """Test listing notes."""
        # Add project and note
        runner.invoke(main, ["project", "add", "--name", "test-project"])
        result = runner.invoke(main, ["project", "list", "--json"])
        project_id = json.loads(result.output)["projects"][0]["id"]
        
        runner.invoke(main, ["note", "add", "Test note", "--project", project_id])
        
        # List notes
        result = runner.invoke(main, ["note", "list", "--project", project_id])
        assert result.exit_code == 0
        assert "Test note" in result.output


class TestSearchCLI:
    """Test search CLI command."""

    def test_search_with_query(self, runner, temp_db):
        """Test searching with a query."""
        # Add project, task, and note
        runner.invoke(main, ["project", "add", "--name", "test-project", "--desc", "Test"])
        result = runner.invoke(main, ["project", "list", "--json"])
        project_id = json.loads(result.output)["projects"][0]["id"]
        
        runner.invoke(main, ["task", "add", "--project", project_id, "--title", "Test task"])
        runner.invoke(main, ["note", "add", "Test note", "--project", project_id])
        
        # Search
        result = runner.invoke(main, ["search", "test"])
        assert result.exit_code == 0
        assert "Found" in result.output

    def test_search_json(self, runner, temp_db):
        """Test searching with JSON output."""
        # Add a project
        runner.invoke(main, ["project", "add", "--name", "alpha-project"])
        
        # Search
        result = runner.invoke(main, ["search", "alpha", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] >= 1

    def test_search_no_query(self, runner, temp_db):
        """Test search without query (returns recent items)."""
        # Add some data
        runner.invoke(main, ["project", "add", "--name", "test-project"])
        
        # Search without query
        result = runner.invoke(main, ["search", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "results" in data