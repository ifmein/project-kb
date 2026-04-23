"""Tests for database operations."""

import os
import tempfile
import time
from pathlib import Path

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import Database
from models import Note, Project, Task


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        yield db
        db.close()


class TestProjectOperations:
    """Test project CRUD operations."""

    def test_create_project(self, temp_db):
        """Test creating a project."""
        project = Project.create(
            name="test-project",
            description="A test project",
            tech_stack="python,sqlite"
        )
        created = temp_db.create_project(project)
        
        assert created.id == project.id
        assert created.name == "test-project"
        assert created.description == "A test project"
        assert created.tech_stack == "python,sqlite"
        assert created.status == "active"

    def test_get_project_by_id(self, temp_db):
        """Test getting project by ID."""
        project = Project.create(name="test-project")
        temp_db.create_project(project)
        
        fetched = temp_db.get_project(project.id)
        assert fetched is not None
        assert fetched.id == project.id
        assert fetched.name == "test-project"

    def test_get_project_by_name(self, temp_db):
        """Test getting project by name."""
        project = Project.create(name="test-project")
        temp_db.create_project(project)
        
        fetched = temp_db.get_project("test-project")
        assert fetched is not None
        assert fetched.id == project.id

    def test_list_projects(self, temp_db):
        """Test listing projects."""
        project1 = Project.create(name="project1", status="active")
        project2 = Project.create(name="project2", status="paused")
        temp_db.create_project(project1)
        temp_db.create_project(project2)
        
        all_projects = temp_db.list_projects()
        assert len(all_projects) == 2
        
        active_projects = temp_db.list_projects(status="active")
        assert len(active_projects) == 1
        assert active_projects[0].name == "project1"

    def test_update_project(self, temp_db):
        """Test updating project fields."""
        project = Project.create(name="test-project")
        temp_db.create_project(project)
        
        updated = temp_db.update_project(project.id, status="paused", description="Updated")
        assert updated.status == "paused"
        assert updated.description == "Updated"
        assert updated.updated_at > project.updated_at

    def test_delete_project(self, temp_db):
        """Test deleting project."""
        project = Project.create(name="test-project")
        temp_db.create_project(project)
        
        success = temp_db.delete_project(project.id)
        assert success is True
        
        fetched = temp_db.get_project(project.id)
        assert fetched is None


class TestTaskOperations:
    """Test task CRUD operations."""

    def test_create_task(self, temp_db):
        """Test creating a task."""
        project = Project.create(name="test-project")
        temp_db.create_project(project)
        
        task = Task.create(
            project_id=project.id,
            title="Test task",
            description="A test task",
            priority="P1"
        )
        created = temp_db.create_task(task)
        
        assert created.id == task.id
        assert created.title == "Test task"
        assert created.priority == "P1"
        assert created.status == "todo"

    def test_get_task(self, temp_db):
        """Test getting task by ID."""
        project = Project.create(name="test-project")
        temp_db.create_project(project)
        
        task = Task.create(project_id=project.id, title="Test task")
        temp_db.create_task(task)
        
        fetched = temp_db.get_task(task.id)
        assert fetched is not None
        assert fetched.id == task.id

    def test_list_tasks(self, temp_db):
        """Test listing tasks with filters."""
        project = Project.create(name="test-project")
        temp_db.create_project(project)
        
        task1 = Task.create(project_id=project.id, title="Task 1", status="todo", priority="P1")
        task2 = Task.create(project_id=project.id, title="Task 2", status="in_progress", priority="P2")
        temp_db.create_task(task1)
        temp_db.create_task(task2)
        
        all_tasks = temp_db.list_tasks(project_id=project.id)
        assert len(all_tasks) == 2
        
        todo_tasks = temp_db.list_tasks(project_id=project.id, status="todo")
        assert len(todo_tasks) == 1
        assert todo_tasks[0].title == "Task 1"

    def test_update_task(self, temp_db):
        """Test updating task fields."""
        project = Project.create(name="test-project")
        temp_db.create_project(project)
        
        task = Task.create(project_id=project.id, title="Test task")
        temp_db.create_task(task)
        
        updated = temp_db.update_task(task.id, status="done", priority="P0")
        assert updated.status == "done"
        assert updated.priority == "P0"

    def test_delete_task(self, temp_db):
        """Test deleting task."""
        project = Project.create(name="test-project")
        temp_db.create_project(project)
        
        task = Task.create(project_id=project.id, title="Test task")
        temp_db.create_task(task)
        
        success = temp_db.delete_task(task.id)
        assert success is True
        
        fetched = temp_db.get_task(task.id)
        assert fetched is None


class TestNoteOperations:
    """Test note CRUD operations."""

    def test_create_note(self, temp_db):
        """Test creating a note."""
        project = Project.create(name="test-project")
        temp_db.create_project(project)
        
        note = Note.create(
            content="Test note content",
            project_id=project.id,
            tags="test,note"
        )
        created = temp_db.create_note(note)
        
        assert created.id == note.id
        assert created.content == "Test note content"
        assert created.tags == "test,note"

    def test_create_global_note(self, temp_db):
        """Test creating a global note (no project)."""
        note = Note.create(content="Global note")
        created = temp_db.create_note(note)
        
        assert created.project_id is None

    def test_get_note(self, temp_db):
        """Test getting note by ID."""
        note = Note.create(content="Test note")
        temp_db.create_note(note)
        
        fetched = temp_db.get_note(note.id)
        assert fetched is not None
        assert fetched.id == note.id

    def test_list_notes(self, temp_db):
        """Test listing notes."""
        project = Project.create(name="test-project")
        temp_db.create_project(project)
        
        note1 = Note.create(content="Note 1", project_id=project.id)
        note2 = Note.create(content="Note 2", project_id=project.id)
        note3 = Note.create(content="Global note")
        
        temp_db.create_note(note1)
        temp_db.create_note(note2)
        temp_db.create_note(note3)
        
        project_notes = temp_db.list_notes(project_id=project.id)
        assert len(project_notes) == 2
        
        all_notes = temp_db.list_notes()
        assert len(all_notes) == 3

    def test_delete_note(self, temp_db):
        """Test deleting note."""
        note = Note.create(content="Test note")
        temp_db.create_note(note)
        
        success = temp_db.delete_note(note.id)
        assert success is True
        
        fetched = temp_db.get_note(note.id)
        assert fetched is None


class TestFTSOperations:
    """Test full-text search operations."""

    def test_fts_sync(self, temp_db):
        """Test that FTS tables sync automatically via triggers."""
        project = Project.create(
            name="test-project",
            description="A project for testing",
            tech_stack="python,sqlite"
        )
        temp_db.create_project(project)
        
        # Search should find the project
        results = temp_db.search("testing")
        assert len(results) == 1
        assert results[0]['name'] == "test-project"

    def test_search_projects(self, temp_db):
        """Test searching projects."""
        project1 = Project.create(name="alpha", description="First project")
        project2 = Project.create(name="beta", description="Second project")
        temp_db.create_project(project1)
        temp_db.create_project(project2)
        
        results = temp_db.search("first")
        assert len(results) == 1
        assert results[0]['name'] == "alpha"

    def test_search_tasks(self, temp_db):
        """Test searching tasks."""
        project = Project.create(name="test-project")
        temp_db.create_project(project)
        
        task1 = Task.create(project_id=project.id, title="Implement login", description="User authentication")
        task2 = Task.create(project_id=project.id, title="Fix bug", description="Login bug")
        temp_db.create_task(task1)
        temp_db.create_task(task2)
        
        results = temp_db.search("login")
        assert len(results) == 2

    def test_search_notes(self, temp_db):
        """Test searching notes."""
        note1 = Note.create(content="Meeting notes about architecture")
        note2 = Note.create(content="Decision: use SQLite")
        temp_db.create_note(note1)
        temp_db.create_note(note2)
        
        results = temp_db.search("architecture")
        assert len(results) == 1
        assert "architecture" in results[0]['content']

    def test_search_with_project_filter(self, temp_db):
        """Test searching within a specific project."""
        project1 = Project.create(name="project1")
        project2 = Project.create(name="project2")
        temp_db.create_project(project1)
        temp_db.create_project(project2)
        
        task1 = Task.create(project_id=project1.id, title="Task in project1")
        task2 = Task.create(project_id=project2.id, title="Task in project2")
        temp_db.create_task(task1)
        temp_db.create_task(task2)
        
        results = temp_db.search("task", project_id=project1.id)
        assert len(results) == 1
        assert results[0]['project_id'] == project1.id

    def test_search_with_type_filter(self, temp_db):
        """Test searching with type filter."""
        project = Project.create(name="test-project", description="Test")
        task = Task.create(project_id=project.id, title="Test task", description="Test")
        note = Note.create(content="Test note")
        
        temp_db.create_project(project)
        temp_db.create_task(task)
        temp_db.create_note(note)
        
        # Search only tasks
        task_results = temp_db.search("test", search_type="task")
        assert len(task_results) == 1
        assert task_results[0]['type'] == 'task'
        
        # Search only notes
        note_results = temp_db.search("test", search_type="note")
        assert len(note_results) == 1
        assert note_results[0]['type'] == 'note'