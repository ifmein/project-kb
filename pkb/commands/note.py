"""Commands: pkb note add/list/show/delete"""

from __future__ import annotations

import click

from pkb import db as _db
from pkb import output as out
from pkb.commands.project import _resolve_project
from pkb.models import fmt_ts, make_id, now
from pkb.options import get_json_flag, json_option


def _row_to_dict(row) -> dict:
    d = dict(row)
    if "created_at" in d and isinstance(d["created_at"], float):
        d["created_at"] = fmt_ts(d["created_at"])
    return d


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------


@click.group("note")
def note() -> None:
    """Manage notes."""


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


@note.command("add")
@click.argument("content")
@click.option("--project", "proj", default=None, help="Project id or name (optional).")
@click.option("--tags", default="", help="Comma-separated tags.")
@json_option
@click.pass_context
def note_add(ctx: click.Context, content: str, proj: str | None, tags: str, as_json: bool) -> None:
    """Add a note (global or project-scoped)."""
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

        note_id = make_id("note")
        ts = now()
        conn.execute(
            "INSERT INTO notes (id, project_id, content, tags, created_at) VALUES (?, ?, ?, ?, ?)",
            (note_id, project_id, content, tags, ts),
        )
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    finally:
        conn.close()

    data = _row_to_dict(row)
    if as_json:
        out.output_json({"success": True, "note": data})
    else:
        out.print_success(f"Note created ({note_id})")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@note.command("list")
@click.option("--project", "proj", default=None, help="Filter by project id or name.")
@click.option("--limit", default=20, show_default=True, help="Max results.")
@json_option
@click.pass_context
def note_list(ctx: click.Context, proj: str | None, limit: int, as_json: bool) -> None:
    """List notes."""
    as_json = get_json_flag(ctx, as_json)
    conn = _db.get_db()
    try:
        if proj:
            project_row = _resolve_project(conn, proj)
            if not project_row:
                conn.close()
                if as_json:
                    out.error_json(f"Project not found: {proj}")
                else:
                    out.print_error(f"Project not found: {proj}")
                return
            rows = conn.execute(
                "SELECT * FROM notes WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
                (project_row["id"], limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM notes ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    finally:
        conn.close()

    data = [_row_to_dict(r) for r in rows]
    if as_json:
        out.output_json({"success": True, "notes": data, "count": len(data)})
    else:
        if not data:
            out.console.print("[dim]No notes found.[/dim]")
        else:
            out.print_notes_table(data)


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------


@note.command("show")
@click.argument("note_id")
@json_option
@click.pass_context
def note_show(ctx: click.Context, note_id: str, as_json: bool) -> None:
    """Show a note's full content."""
    as_json = get_json_flag(ctx, as_json)
    conn = _db.get_db()
    try:
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        if as_json:
            out.error_json(f"Note not found: {note_id}")
        else:
            out.print_error(f"Note not found: {note_id}")
        return

    data = _row_to_dict(row)
    if as_json:
        out.output_json({"success": True, "note": data})
    else:
        out.print_note_panel(data)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


@note.command("delete")
@click.argument("note_id")
@click.option("--yes", is_flag=True, default=False, help="Skip confirmation.")
@json_option
@click.pass_context
def note_delete(ctx: click.Context, note_id: str, yes: bool, as_json: bool) -> None:
    """Delete a note."""
    as_json = get_json_flag(ctx, as_json)
    conn = _db.get_db()
    try:
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not row:
            conn.close()
            if as_json:
                out.error_json(f"Note not found: {note_id}")
            else:
                out.print_error(f"Note not found: {note_id}")
            return

        if not yes and not as_json:
            click.confirm(f"Delete note '{note_id}'?", abort=True)

        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    finally:
        conn.close()

    if as_json:
        out.output_json({"success": True, "deleted_id": note_id})
    else:
        out.print_success(f"Note [bold]{note_id}[/bold] deleted.")
