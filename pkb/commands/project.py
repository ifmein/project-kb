"""Commands: pkb project list/add/show/update/delete"""

from __future__ import annotations

import click

from pkb import db as _db, output as out
from pkb.models import make_id, now, fmt_ts
from pkb.options import json_option, get_json_flag


def _resolve_project(conn, id_or_name: str):
    """Return a project Row or None, matching by id OR name."""
    return conn.execute(
        "SELECT * FROM projects WHERE id = ? OR name = ?",
        (id_or_name, id_or_name),
    ).fetchone()


def _task_stats(conn, project_id: str) -> dict:
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM tasks WHERE project_id = ? GROUP BY status",
        (project_id,),
    ).fetchall()
    return {r["status"]: r["cnt"] for r in rows}


def _row_to_dict(row) -> dict:
    d = dict(row)
    for key in ("created_at", "updated_at"):
        if key in d and isinstance(d[key], float):
            d[key] = fmt_ts(d[key])
    return d


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------


@click.group("project")
def project() -> None:
    """Manage projects."""


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@project.command("list")
@click.option("--status", "status_filter", default=None, help="Filter by status.")
@json_option
@click.pass_context
def project_list(ctx: click.Context, status_filter: str | None, as_json: bool) -> None:
    """List all projects."""
    as_json = get_json_flag(ctx, as_json)
    conn = _db.get_db()
    try:
        if status_filter:
            rows = conn.execute(
                "SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC",
                (status_filter,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
    finally:
        conn.close()

    data = [_row_to_dict(r) for r in rows]
    if as_json:
        out.output_json({"success": True, "projects": data, "count": len(data)})
    else:
        if not data:
            out.console.print("[dim]No projects found.[/dim]")
        else:
            out.print_projects_table(data)


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


@project.command("add")
@click.option("--name", required=True, help="Project name (unique).")
@click.option("--desc", default="", help="Project description.")
@click.option("--status", "status", default="active", help="Status (default: active).")
@click.option("--repo", "repo_url", default="", help="Repository URL.")
@click.option("--tech", "tech_stack", default="", help="Tech stack (comma-separated).")
@json_option
@click.pass_context
def project_add(
    ctx: click.Context,
    name: str,
    desc: str,
    status: str,
    repo_url: str,
    tech_stack: str,
    as_json: bool,
) -> None:
    """Create a new project."""
    as_json = get_json_flag(ctx, as_json)
    proj_id = make_id("proj")
    ts = now()
    conn = _db.get_db()
    try:
        conn.execute(
            """
            INSERT INTO projects (id, name, description, status, repo_url, tech_stack, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (proj_id, name, desc, status, repo_url, tech_stack, ts, ts),
        )
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (proj_id,)).fetchone()
    finally:
        conn.close()

    data = _row_to_dict(row)
    if as_json:
        out.output_json({"success": True, "project": data})
    else:
        out.print_success(f"Project [bold]{name}[/bold] created ({proj_id})")


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------


@project.command("show")
@click.argument("id_or_name")
@json_option
@click.pass_context
def project_show(ctx: click.Context, id_or_name: str, as_json: bool) -> None:
    """Show project details with task statistics."""
    as_json = get_json_flag(ctx, as_json)
    conn = _db.get_db()
    try:
        row = _resolve_project(conn, id_or_name)
        if not row:
            conn.close()
            if as_json:
                out.error_json(f"Project not found: {id_or_name}")
            else:
                out.print_error(f"Project not found: {id_or_name}")
            return
        stats = _task_stats(conn, row["id"])
    finally:
        conn.close()

    data = _row_to_dict(row)
    if as_json:
        out.output_json({"success": True, "project": data, "task_stats": stats})
    else:
        out.print_project_panel(data, task_stats=stats)


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


@project.command("update")
@click.argument("id_or_name")
@click.option("--name", default=None)
@click.option("--desc", default=None)
@click.option("--status", default=None)
@click.option("--repo", "repo_url", default=None)
@click.option("--tech", "tech_stack", default=None)
@json_option
@click.pass_context
def project_update(
    ctx: click.Context,
    id_or_name: str,
    name: str | None,
    desc: str | None,
    status: str | None,
    repo_url: str | None,
    tech_stack: str | None,
    as_json: bool,
) -> None:
    """Update project fields."""
    as_json = get_json_flag(ctx, as_json)
    fields: dict[str, str] = {}
    if name is not None:
        fields["name"] = name
    if desc is not None:
        fields["description"] = desc
    if status is not None:
        fields["status"] = status
    if repo_url is not None:
        fields["repo_url"] = repo_url
    if tech_stack is not None:
        fields["tech_stack"] = tech_stack

    if not fields:
        if as_json:
            out.error_json("No fields to update.")
        else:
            out.print_error("No fields to update.")
        return

    conn = _db.get_db()
    try:
        row = _resolve_project(conn, id_or_name)
        if not row:
            conn.close()
            if as_json:
                out.error_json(f"Project not found: {id_or_name}")
            else:
                out.print_error(f"Project not found: {id_or_name}")
            return

        fields["updated_at"] = str(now())
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [row["id"]]
        conn.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", values)  # noqa: S608
        updated = conn.execute("SELECT * FROM projects WHERE id = ?", (row["id"],)).fetchone()
    finally:
        conn.close()

    data = _row_to_dict(updated)
    if as_json:
        out.output_json({"success": True, "project": data})
    else:
        out.print_success(f"Project [bold]{row['name']}[/bold] updated.")


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


@project.command("delete")
@click.argument("id_or_name")
@click.option("--yes", is_flag=True, default=False, help="Skip confirmation.")
@json_option
@click.pass_context
def project_delete(ctx: click.Context, id_or_name: str, yes: bool, as_json: bool) -> None:
    """Delete a project (cascades to tasks and notes)."""
    as_json = get_json_flag(ctx, as_json)
    conn = _db.get_db()
    try:
        row = _resolve_project(conn, id_or_name)
        if not row:
            conn.close()
            if as_json:
                out.error_json(f"Project not found: {id_or_name}")
            else:
                out.print_error(f"Project not found: {id_or_name}")
            return

        if not yes and not as_json:
            click.confirm(f"Delete project '{row['name']}' and all its tasks/notes?", abort=True)

        conn.execute("DELETE FROM projects WHERE id = ?", (row["id"],))
    finally:
        conn.close()

    if as_json:
        out.output_json({"success": True, "deleted_id": row["id"], "name": row["name"]})
    else:
        out.print_success(f"Project [bold]{row['name']}[/bold] deleted.")
