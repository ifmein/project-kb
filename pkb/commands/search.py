"""Command: pkb search — FTS5 full-text search across tasks and notes."""

from __future__ import annotations

import click

from pkb import db as _db, output as out
from pkb.models import fmt_ts
from pkb.options import json_option, get_json_flag
from pkb.commands.project import _resolve_project


def _search_db(
    conn,
    query: str,
    project_id: str | None = None,
    type_filter: str | None = None,
) -> list[dict]:
    """Run FTS5 UNION query and return result dicts ordered by relevance."""

    results: list[dict] = []

    # ---------------------------------------------------------------- projects
    # Skipped when --project filter is active (already scoped) or --type task/note.
    if type_filter in (None, "project") and project_id is None:
        sql = """
            SELECT
                p.id, p.name, p.description, p.status, p.created_at,
                projects_fts.rank AS rank
            FROM projects_fts
            JOIN projects p ON projects_fts.rowid = p.rowid
            WHERE projects_fts MATCH ?
            ORDER BY rank
        """
        for r in conn.execute(sql, (query,)).fetchall():
            results.append(
                {
                    "type": "project",
                    "id": r["id"],
                    "name": r["name"],
                    "description": r["description"],
                    "status": r["status"],
                    "created_at": fmt_ts(r["created_at"]),
                    "_rank": r["rank"],
                }
            )

    # ------------------------------------------------------------------ notes
    if type_filter in (None, "note"):
        if project_id:
            sql = """
                SELECT
                    n.id, n.project_id, n.content, n.tags, n.created_at,
                    notes_fts.rank AS rank
                FROM notes_fts
                JOIN notes n ON notes_fts.rowid = n.rowid
                WHERE notes_fts MATCH ?
                  AND n.project_id = ?
                ORDER BY rank
            """
            rows = conn.execute(sql, (query, project_id)).fetchall()
        else:
            sql = """
                SELECT
                    n.id, n.project_id, n.content, n.tags, n.created_at,
                    notes_fts.rank AS rank
                FROM notes_fts
                JOIN notes n ON notes_fts.rowid = n.rowid
                WHERE notes_fts MATCH ?
                ORDER BY rank
            """
            rows = conn.execute(sql, (query,)).fetchall()

        for r in rows:
            proj_name: str | None = None
            if r["project_id"]:
                proj_row = conn.execute("SELECT name FROM projects WHERE id = ?", (r["project_id"],)).fetchone()
                proj_name = proj_row["name"] if proj_row else r["project_id"]

            results.append(
                {
                    "type": "note",
                    "id": r["id"],
                    "project": proj_name,
                    "content": r["content"],
                    "tags": r["tags"] or "",
                    "created_at": fmt_ts(r["created_at"]),
                    "_rank": r["rank"],
                }
            )

    # ------------------------------------------------------------------ tasks
    if type_filter in (None, "task"):
        if project_id:
            sql = """
                SELECT
                    t.id, t.project_id, t.title, t.description,
                    t.status, t.priority, t.created_at,
                    tasks_fts.rank AS rank
                FROM tasks_fts
                JOIN tasks t ON tasks_fts.rowid = t.rowid
                WHERE tasks_fts MATCH ?
                  AND t.project_id = ?
                ORDER BY rank
            """
            rows = conn.execute(sql, (query, project_id)).fetchall()
        else:
            sql = """
                SELECT
                    t.id, t.project_id, t.title, t.description,
                    t.status, t.priority, t.created_at,
                    tasks_fts.rank AS rank
                FROM tasks_fts
                JOIN tasks t ON tasks_fts.rowid = t.rowid
                WHERE tasks_fts MATCH ?
                ORDER BY rank
            """
            rows = conn.execute(sql, (query,)).fetchall()

        for r in rows:
            proj_name = None
            if r["project_id"]:
                proj_row = conn.execute("SELECT name FROM projects WHERE id = ?", (r["project_id"],)).fetchone()
                proj_name = proj_row["name"] if proj_row else r["project_id"]

            results.append(
                {
                    "type": "task",
                    "id": r["id"],
                    "project": proj_name,
                    "title": r["title"],
                    "status": r["status"],
                    "priority": r["priority"],
                    "created_at": fmt_ts(r["created_at"]),
                    "_rank": r["rank"],
                }
            )

    # Sort by FTS rank (more negative = more relevant → ascending)
    results.sort(key=lambda x: x["_rank"])
    # Strip internal rank field before returning
    for r in results:
        del r["_rank"]

    return results


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


@click.command("search")
@click.argument("query")
@click.option("--project", "proj", default=None, help="Limit to a project id or name.")
@click.option(
    "--type",
    "type_filter",
    default=None,
    type=click.Choice(["task", "note", "project"], case_sensitive=False),
    help="Limit to a result type.",
)
@json_option
@click.pass_context
def search(ctx: click.Context, query: str, proj: str | None, type_filter: str | None, as_json: bool) -> None:
    """Full-text search across tasks and notes (Chinese + pinyin)."""
    as_json = get_json_flag(ctx, as_json)

    conn = _db.get_db()
    try:
        project_id: str | None = None
        if proj:
            project_row = _resolve_project(conn, proj)
            if not project_row:
                conn.close()
                if as_json:
                    out.error_json(f"Project not found: {proj}")
                else:
                    out.print_error(f"Project not found: {proj}")
                return
            project_id = project_row["id"]

        try:
            results = _search_db(conn, query, project_id=project_id, type_filter=type_filter)
        except Exception as exc:
            conn.close()
            if as_json:
                out.error_json(f"Search error: {exc}")
            else:
                out.print_error(f"Search error: {exc}")
            return
    finally:
        conn.close()

    payload = {"success": True, "query": query, "results": results, "count": len(results)}
    if as_json:
        out.output_json(payload)
    else:
        out.print_search_results(results, query)
