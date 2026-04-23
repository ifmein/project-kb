"""Database operations for Project Knowledge Base."""

import sqlite3
import time
from pathlib import Path
from typing import List, Optional, Tuple, Union

from models import Note, Project, Task

DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "pkb" / "pkb.db"


class Database:
    """SQLite database manager for pkb."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        """Initialize tables, FTS5 virtual tables, and triggers."""
        cursor = self.conn.cursor()
        
        # Main tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                repo_url TEXT DEFAULT '',
                tech_stack TEXT DEFAULT '',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'todo',
                priority TEXT DEFAULT 'P2',
                assignee TEXT DEFAULT '',
                due_date TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '',
                created_at REAL NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)
        
        # FTS5 virtual tables
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS projects_fts USING fts5(
                name, description, tech_stack,
                content=projects,
                content_rowid=rowid
            )
        """)
        
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
                title, description,
                content=tasks,
                content_rowid=rowid
            )
        """)
        
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                content, tags,
                content=notes,
                content_rowid=rowid
            )
        """)
        
        # Triggers for FTS5 sync
        self._create_triggers(cursor)
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        self.conn.commit()

    def _create_triggers(self, cursor):
        """Create triggers to sync FTS5 tables with main tables."""
        # Projects triggers
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS projects_ai AFTER INSERT ON projects BEGIN
                INSERT INTO projects_fts(rowid, name, description, tech_stack)
                VALUES (new.rowid, new.name, new.description, new.tech_stack);
            END
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS projects_ad AFTER DELETE ON projects BEGIN
                INSERT INTO projects_fts(projects_fts, rowid, name, description, tech_stack)
                VALUES ('delete', old.rowid, old.name, old.description, old.tech_stack);
            END
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS projects_au AFTER UPDATE ON projects BEGIN
                INSERT INTO projects_fts(projects_fts, rowid, name, description, tech_stack)
                VALUES ('delete', old.rowid, old.name, old.description, old.tech_stack);
                INSERT INTO projects_fts(rowid, name, description, tech_stack)
                VALUES (new.rowid, new.name, new.description, new.tech_stack);
            END
        """)
        
        # Tasks triggers
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS tasks_ai AFTER INSERT ON tasks BEGIN
                INSERT INTO tasks_fts(rowid, title, description)
                VALUES (new.rowid, new.title, new.description);
            END
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS tasks_ad AFTER DELETE ON tasks BEGIN
                INSERT INTO tasks_fts(tasks_fts, rowid, title, description)
                VALUES ('delete', old.rowid, old.title, old.description);
            END
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS tasks_au AFTER UPDATE ON tasks BEGIN
                INSERT INTO tasks_fts(tasks_fts, rowid, title, description)
                VALUES ('delete', old.rowid, old.title, old.description);
                INSERT INTO tasks_fts(rowid, title, description)
                VALUES (new.rowid, new.title, new.description);
            END
        """)
        
        # Notes triggers
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
                INSERT INTO notes_fts(rowid, content, tags)
                VALUES (new.rowid, new.content, new.tags);
            END
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
                INSERT INTO notes_fts(notes_fts, rowid, content, tags)
                VALUES ('delete', old.rowid, old.content, old.tags);
            END
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
                INSERT INTO notes_fts(notes_fts, rowid, content, tags)
                VALUES ('delete', old.rowid, old.content, old.tags);
                INSERT INTO notes_fts(rowid, content, tags)
                VALUES (new.rowid, new.content, new.tags);
            END
        """)

    # Project operations
    def create_project(self, project: Project) -> Project:
        """Insert a new project."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO projects (id, name, description, status, repo_url, tech_stack, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (project.id, project.name, project.description, project.status,
              project.repo_url, project.tech_stack, project.created_at, project.updated_at))
        self.conn.commit()
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID or name."""
        cursor = self.conn.cursor()
        # Try by ID first
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        if not row:
            # Try by name
            cursor.execute("SELECT * FROM projects WHERE name = ?", (project_id,))
            row = cursor.fetchone()
        if not row:
            return None
        return Project(**dict(row))

    def list_projects(self, status: Optional[str] = None) -> List[Project]:
        """List all projects, optionally filtered by status."""
        cursor = self.conn.cursor()
        if status:
            cursor.execute("SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC", (status,))
        else:
            cursor.execute("SELECT * FROM projects ORDER BY updated_at DESC")
        return [Project(**dict(row)) for row in cursor.fetchall()]

    def update_project(self, project_id: str, **kwargs) -> Optional[Project]:
        """Update project fields."""
        if not kwargs:
            return self.get_project(project_id)
        
        kwargs['updated_at'] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [project_id]
        
        cursor = self.conn.cursor()
        cursor.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", values)
        self.conn.commit()
        return self.get_project(project_id)

    def delete_project(self, project_id: str) -> bool:
        """Delete project and cascade to tasks/notes."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # Task operations
    def create_task(self, task: Task) -> Task:
        """Insert a new task."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (id, project_id, title, description, status, priority, assignee, due_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (task.id, task.project_id, task.title, task.description,
              task.status, task.priority, task.assignee, task.due_date,
              task.created_at, task.updated_at))
        self.conn.commit()
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Task(**dict(row))

    def list_tasks(self, project_id: Optional[str] = None, status: Optional[str] = None,
                   priority: Optional[str] = None) -> List[Task]:
        """List tasks with optional filters."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        
        query += " ORDER BY updated_at DESC"
        cursor.execute(query, params)
        return [Task(**dict(row)) for row in cursor.fetchall()]

    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        """Update task fields."""
        if not kwargs:
            return self.get_task(task_id)
        
        kwargs['updated_at'] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [task_id]
        
        cursor = self.conn.cursor()
        cursor.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
        self.conn.commit()
        return self.get_task(task_id)

    def delete_task(self, task_id: str) -> bool:
        """Delete task."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # Note operations
    def create_note(self, note: Note) -> Note:
        """Insert a new note."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO notes (id, project_id, content, tags, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (note.id, note.project_id, note.content, note.tags, note.created_at))
        self.conn.commit()
        return note

    def get_note(self, note_id: str) -> Optional[Note]:
        """Get note by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Note(**dict(row))

    def list_notes(self, project_id: Optional[str] = None, limit: int = 50) -> List[Note]:
        """List notes, optionally filtered by project."""
        cursor = self.conn.cursor()
        if project_id:
            cursor.execute("SELECT * FROM notes WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
                           (project_id, limit))
        else:
            cursor.execute("SELECT * FROM notes ORDER BY created_at DESC LIMIT ?", (limit,))
        return [Note(**dict(row)) for row in cursor.fetchall()]

    def delete_note(self, note_id: str) -> bool:
        """Delete note."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # Search operations
    def search(self, query: str, project_id: Optional[str] = None,
               search_type: Optional[str] = None) -> List[dict]:
        """Full-text search across projects, tasks, and notes."""
        cursor = self.conn.cursor()
        results = []
        
        # Search projects
        if not search_type or search_type == "project":
            sql = """
                SELECT p.*, projects_fts.rank
                FROM projects_fts
                JOIN projects p ON p.rowid = projects_fts.rowid
                WHERE projects_fts MATCH ?
            """
            params = [query]
            if project_id:
                sql += " AND p.id = ?"
                params.append(project_id)
            sql += " ORDER BY projects_fts.rank"
            
            cursor.execute(sql, params)
            for row in cursor.fetchall():
                row_dict = dict(row)
                row_dict['type'] = 'project'
                results.append(row_dict)
        
        # Search tasks
        if not search_type or search_type == "task":
            sql = """
                SELECT t.*, tasks_fts.rank
                FROM tasks_fts
                JOIN tasks t ON t.rowid = tasks_fts.rowid
                WHERE tasks_fts MATCH ?
            """
            params = [query]
            if project_id:
                sql += " AND t.project_id = ?"
                params.append(project_id)
            sql += " ORDER BY tasks_fts.rank"
            
            cursor.execute(sql, params)
            for row in cursor.fetchall():
                row_dict = dict(row)
                row_dict['type'] = 'task'
                results.append(row_dict)
        
        # Search notes
        if not search_type or search_type == "note":
            sql = """
                SELECT n.*, notes_fts.rank
                FROM notes_fts
                JOIN notes n ON n.rowid = notes_fts.rowid
                WHERE notes_fts MATCH ?
            """
            params = [query]
            if project_id:
                sql += " AND n.project_id = ?"
                params.append(project_id)
            sql += " ORDER BY notes_fts.rank"
            
            cursor.execute(sql, params)
            for row in cursor.fetchall():
                row_dict = dict(row)
                row_dict['type'] = 'note'
                results.append(row_dict)
        
        # Sort all results by rank (most relevant first)
        results.sort(key=lambda x: x.get('rank', 0))
        return results

    def close(self):
        """Close database connection."""
        self.conn.close()