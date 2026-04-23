"""Tests for search functionality."""

import tempfile
from pathlib import Path

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import Database
from models import Note, Project, Task
from search import format_search_results, format_timestamp, get_recent_items, search


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        yield db
        db.close()


class TestSearchFunction:
    """Test search function."""

    def test_search_returns_formatted_results(self, temp_db):
        """Test that search returns properly formatted results."""
        # Add test data
        project = Project.create(name="test-project", description="A test project")
        temp_db.create_project(project)
        
        task = Task.create(project_id=project.id, title="Test task", description="Task description")
        temp_db.create_task(task)
        
        note = Note.create(content="Test note content", project_id=project.id)
        temp_db.create_note(note)
        
        # Search
        results = search("test", db=temp_db)
        
        assert results["success"] is True
        assert results["query"] == "test"
        assert results["count"] >= 1
        assert "results" in results
        
        # Check that rank is not in results (as per PRD)
        for item in results["results"]:
            assert "rank" not in item

    def test_search_with_project_filter(self, temp_db):
        """Test search with project filter."""
        project1 = Project.create(name="project1")
        project2 = Project.create(name="project2")
        temp_db.create_project(project1)
        temp_db.create_project(project2)
        
        task1 = Task.create(project_id=project1.id, title="Task in project1")
        task2 = Task.create(project_id=project2.id, title="Task in project2")
        temp_db.create_task(task1)
        temp_db.create_task(task2)
        
        # Search within project1
        results = search("task", project_id=project1.id, db=temp_db)
        
        assert results["success"] is True
        # All results should be from project1
        for item in results["results"]:
            if "project_id" in item:
                assert item["project_id"] == project1.id

    def test_search_with_type_filter(self, temp_db):
        """Test search with type filter."""
        project = Project.create(name="test-project", description="Test")
        task = Task.create(project_id=project.id, title="Test task", description="Test")
        note = Note.create(content="Test note")
        
        temp_db.create_project(project)
        temp_db.create_task(task)
        temp_db.create_note(note)
        
        # Search only tasks
        task_results = search("test", search_type="task", db=temp_db)
        assert task_results["success"] is True
        for item in task_results["results"]:
            assert item["type"] == "task"
        
        # Search only notes
        note_results = search("test", search_type="note", db=temp_db)
        assert note_results["success"] is True
        for item in note_results["results"]:
            assert item["type"] == "note"


class TestRecentItems:
    """Test get_recent_items function."""

    def test_get_recent_items_no_data(self, temp_db):
        """Test get_recent_items with empty database."""
        results = get_recent_items(db=temp_db)
        
        assert results["success"] is True
        assert results["count"] == 0
        assert results["results"] == []

    def test_get_recent_items_with_data(self, temp_db):
        """Test get_recent_items with data."""
        # Add some data
        project = Project.create(name="test-project")
        task = Task.create(project_id=project.id, title="Test task")
        note = Note.create(content="Test note")
        
        temp_db.create_project(project)
        temp_db.create_task(task)
        temp_db.create_note(note)
        
        results = get_recent_items(limit=5, db=temp_db)
        
        assert results["success"] is True
        assert results["count"] >= 1
        assert "results" in results
        
        # Check that each item has required fields
        for item in results["results"]:
            assert "type" in item
            assert "id" in item
            assert "created_at" in item

    def test_get_recent_items_limit(self, temp_db):
        """Test get_recent_items respects limit."""
        # Add multiple items
        for i in range(10):
            project = Project.create(name=f"project-{i}")
            temp_db.create_project(project)
        
        results = get_recent_items(limit=5, db=temp_db)
        
        assert results["success"] is True
        assert results["count"] <= 5


class TestFormatTimestamp:
    """Test format_timestamp function."""

    def test_format_timestamp(self):
        """Test timestamp formatting."""
        # Test with a known timestamp (2026-04-23 08:00:00 UTC)
        ts = 1776892800.0
        formatted = format_timestamp(ts)
        assert formatted == "2026-04-23"


class TestFormatSearchResults:
    """Test format_search_results function."""

    def test_format_search_results(self):
        """Test search results formatting."""
        results = [
            {
                "type": "project",
                "id": "proj_123",
                "name": "test",
                "rank": -0.5,
                "created_at": 1776892800.0,
                "updated_at": 1776892800.0
            },
            {
                "type": "task",
                "id": "task_456",
                "title": "Test task",
                "rank": -0.3,
                "created_at": 1776892800.0,
                "updated_at": 1776892800.0
            }
        ]
        
        formatted = format_search_results(results, "test")
        
        assert formatted["success"] is True
        assert formatted["query"] == "test"
        assert formatted["count"] == 2
        
        # Check that rank is removed
        for item in formatted["results"]:
            assert "rank" not in item
            # Check timestamps are formatted
            assert isinstance(item["created_at"], str)
            assert isinstance(item["updated_at"], str)