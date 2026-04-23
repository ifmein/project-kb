"""Data models for Project Knowledge Base."""

import time
from dataclasses import dataclass, field
from typing import Optional

from nanoid import generate

# ID prefixes
PROJECT_PREFIX = "proj_"
TASK_PREFIX = "task_"
NOTE_PREFIX = "note_"


def generate_id(prefix: str) -> str:
    """Generate a unique ID with given prefix."""
    return f"{prefix}{generate(size=12)}"


@dataclass
class Project:
    """Project model."""
    id: str
    name: str
    description: str = ""
    status: str = "active"  # active / paused / completed / archived
    repo_url: str = ""
    tech_stack: str = ""  # comma-separated
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @classmethod
    def create(cls, name: str, description: str = "", **kwargs) -> "Project":
        """Create a new project with generated ID and timestamps."""
        now = time.time()
        return cls(
            id=generate_id(PROJECT_PREFIX),
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
            **kwargs,
        )


@dataclass
class Task:
    """Task model."""
    id: str
    project_id: str
    title: str
    description: str = ""
    status: str = "todo"  # todo / in_progress / done / cancelled
    priority: str = "P2"  # P0 / P1 / P2 / P3
    assignee: str = ""
    due_date: Optional[str] = None  # ISO 8601
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @classmethod
    def create(cls, project_id: str, title: str, **kwargs) -> "Task":
        """Create a new task with generated ID and timestamps."""
        now = time.time()
        return cls(
            id=generate_id(TASK_PREFIX),
            project_id=project_id,
            title=title,
            created_at=now,
            updated_at=now,
            **kwargs,
        )


@dataclass
class Note:
    """Note model."""
    id: str
    project_id: Optional[str]  # can be None for global notes
    content: str
    tags: str = ""  # comma-separated
    created_at: float = field(default_factory=time.time)

    @classmethod
    def create(cls, content: str, project_id: Optional[str] = None, **kwargs) -> "Note":
        """Create a new note with generated ID and timestamp."""
        return cls(
            id=generate_id(NOTE_PREFIX),
            project_id=project_id,
            content=content,
            created_at=time.time(),
            **kwargs,
        )