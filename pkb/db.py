"""Database layer: connection, schema initialization, FTS5 + triggers."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

_DEFAULT_DB = Path.home() / ".config" / "project-kb" / "pkb.db"
_DEFAULT_EXT = Path.home() / ".config" / "project-kb" / "libsimple"


def get_db(path: str | Path | None = None) -> sqlite3.Connection:
    """Return a sqlite3 connection.

    Resolution order for the DB path:
    1. ``path`` argument
    2. ``PKB_DB_PATH`` environment variable
    3. ``~/.config/project-kb/pkb.db``
    """
    db_path = Path(path) if path else Path(os.environ.get("PKB_DB_PATH", str(_DEFAULT_DB)))
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    # Auto-load the simple tokenizer extension on every connection so FTS5
    # queries work without the caller having to remember to call load_extension().
    load_extension(conn)
    return conn


# ---------------------------------------------------------------------------
# Extension loading
# ---------------------------------------------------------------------------


def _resolve_ext_path() -> str:
    """Return the extension path to try, or '' if nothing is available.

    Resolution order:
    1. PKB_SIMPLE_EXT env var (explicit)
    2. ~/.config/project-kb/libsimple (default install location from pkb init)
    """
    from_env = os.environ.get("PKB_SIMPLE_EXT", "")
    if from_env:
        return from_env
    if (_DEFAULT_EXT.with_suffix(".dylib")).exists() or Path(str(_DEFAULT_EXT) + ".so").exists():
        return str(_DEFAULT_EXT)
    return ""


def _get_tokenizer(conn: sqlite3.Connection) -> str:
    """Load the simple tokenizer extension.  Returns the tokenize= string."""
    ext_path = _resolve_ext_path()
    if not ext_path:
        return "unicode61"

    # SQLite extension loading requires enable_load_extension
    try:
        conn.enable_load_extension(True)
        conn.load_extension(ext_path)
        conn.enable_load_extension(False)
        return "simple"
    except Exception:
        return "unicode61"


def load_extension(conn: sqlite3.Connection) -> bool:
    """Load the simple tokenizer; return True if successful."""
    ext_path = _resolve_ext_path()
    if not ext_path:
        return False
    try:
        conn.enable_load_extension(True)
        conn.load_extension(ext_path)
        conn.enable_load_extension(False)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_DDL_TABLES = """
CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'active',
    repo_url    TEXT NOT NULL DEFAULT '',
    local_path  TEXT NOT NULL DEFAULT '',
    tech_stack  TEXT NOT NULL DEFAULT '',
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'todo',
    priority    TEXT NOT NULL DEFAULT 'P2',
    assignee    TEXT NOT NULL DEFAULT '',
    due_date    TEXT NOT NULL DEFAULT '',
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS notes (
    id          TEXT PRIMARY KEY,
    project_id  TEXT REFERENCES projects(id) ON DELETE CASCADE,
    content     TEXT NOT NULL,
    tags        TEXT NOT NULL DEFAULT '',
    created_at  REAL NOT NULL
);
"""

# FTS5 virtual tables — tokenizer filled in at runtime
_DDL_FTS_TEMPLATE = """
CREATE VIRTUAL TABLE IF NOT EXISTS projects_fts USING fts5(
    name, description,
    content=projects,
    content_rowid=rowid,
    tokenize='{tokenizer}'
);

CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    content,
    content=notes,
    content_rowid=rowid,
    tokenize='{tokenizer}'
);

CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
    title, description,
    content=tasks,
    content_rowid=rowid,
    tokenize='{tokenizer}'
);
"""

_DDL_TRIGGERS = """
-- projects_fts triggers
CREATE TRIGGER IF NOT EXISTS projects_fts_insert
AFTER INSERT ON projects BEGIN
    INSERT INTO projects_fts(rowid, name, description) VALUES (new.rowid, new.name, new.description);
END;

CREATE TRIGGER IF NOT EXISTS projects_fts_delete
AFTER DELETE ON projects BEGIN
    INSERT INTO projects_fts(projects_fts, rowid, name, description)
    VALUES ('delete', old.rowid, old.name, old.description);
END;

CREATE TRIGGER IF NOT EXISTS projects_fts_update
AFTER UPDATE ON projects BEGIN
    INSERT INTO projects_fts(projects_fts, rowid, name, description)
    VALUES ('delete', old.rowid, old.name, old.description);
    INSERT INTO projects_fts(rowid, name, description) VALUES (new.rowid, new.name, new.description);
END;

-- notes_fts triggers
CREATE TRIGGER IF NOT EXISTS notes_fts_insert
AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(rowid, content) VALUES (new.rowid, new.content);
END;

CREATE TRIGGER IF NOT EXISTS notes_fts_delete
AFTER DELETE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, content) VALUES ('delete', old.rowid, old.content);
END;

CREATE TRIGGER IF NOT EXISTS notes_fts_update
AFTER UPDATE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, content) VALUES ('delete', old.rowid, old.content);
    INSERT INTO notes_fts(rowid, content) VALUES (new.rowid, new.content);
END;

-- tasks_fts triggers
CREATE TRIGGER IF NOT EXISTS tasks_fts_insert
AFTER INSERT ON tasks BEGIN
    INSERT INTO tasks_fts(rowid, title, description) VALUES (new.rowid, new.title, new.description);
END;

CREATE TRIGGER IF NOT EXISTS tasks_fts_delete
AFTER DELETE ON tasks BEGIN
    INSERT INTO tasks_fts(tasks_fts, rowid, title, description)
    VALUES ('delete', old.rowid, old.title, old.description);
END;

CREATE TRIGGER IF NOT EXISTS tasks_fts_update
AFTER UPDATE ON tasks BEGIN
    INSERT INTO tasks_fts(tasks_fts, rowid, title, description)
    VALUES ('delete', old.rowid, old.title, old.description);
    INSERT INTO tasks_fts(rowid, title, description) VALUES (new.rowid, new.title, new.description);
END;
"""

_DDL_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status  ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_notes_project ON notes(project_id);
"""


def init_db(conn: sqlite3.Connection) -> str:
    """Create all tables, FTS virtual tables, triggers, and indexes.

    Returns the tokenizer name that was used ('simple' or 'unicode61').
    """
    tokenizer = _get_tokenizer(conn)

    conn.executescript(_DDL_TABLES)
    conn.executescript(_DDL_FTS_TEMPLATE.format(tokenizer=tokenizer))
    conn.executescript(_DDL_TRIGGERS)
    conn.executescript(_DDL_INDEXES)

    # Schema migrations — ADD COLUMN is idempotent via the exception check
    _migrate(conn)

    # Backfill FTS indexes from existing data (safe to run repeatedly;
    # FTS5 'rebuild' re-reads the content table from scratch).
    conn.execute("INSERT INTO projects_fts(projects_fts) VALUES('rebuild')")
    conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")
    conn.execute("INSERT INTO tasks_fts(tasks_fts) VALUES('rebuild')")

    return tokenizer


def _migrate(conn: sqlite3.Connection) -> None:
    """Apply incremental column additions to existing databases."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(projects)").fetchall()}
    if "local_path" not in existing:
        conn.execute("ALTER TABLE projects ADD COLUMN local_path TEXT NOT NULL DEFAULT ''")
