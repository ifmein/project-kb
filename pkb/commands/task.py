"""Commands: pkb task list/add/show/update/done/delete"""

from __future__ import annotations

import click

from pkb import db as _db
from pkb import output as out
from pkb.commands.project import _resolve_project
from pkb.models import fmt_ts, make_id, now
from pkb.options import get_json_flag, json_option


def _resolve_task(conn, task_id: str):
    return conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()


def _row_to_dict(row) -> dict:
    d = dict(row)
    for key in ("created_at", "updated_at"):
        if key in d and isinstance(d[key], float):
            d[key] = fmt_ts(d[key])
    return d


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------


@click.group("task")
def task() -> None:
    """Manage tasks."""


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@task.command("list")
@click.option("--project", "proj", default=None, help="Project id or name.")
@click.option("--status", "status_filter", default=None, help="Filter by status.")
@click.option("--priority", "priority_filter", default=None, help="Filter by priority.")
@json_option
@click.pass_context
def task_list(
    ctx: click.Context,
    proj: str | None,
    status_filter: str | None,
    priority_filter: str | None,
    as_json: bool,
) -> None:
    """List tasks, optionally filtered by project."""
    as_json = get_json_flag(ctx, as_json)
    conn = _db.get_db()
    try:
        conditions: list[str] = []
        params: list[str] = []
        if proj:
            project_row = _resolve_project(conn, proj)
            if not project_row:
                conn.close()
                if as_json:
                    out.error_json(f"Project not found: {proj}")
                else:
                    out.print_error(f"Project not found: {proj}")
                return

            conditions.append("project_id = ?")
            params.append(project_row["id"])

        if status_filter:
            conditions.append("status = ?")
            params.append(status_filter)
        if priority_filter:
            conditions.append("priority = ?")
            params.append(priority_filter)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = conn.execute(
            f"SELECT * FROM tasks {where} ORDER BY priority ASC, created_at DESC",  # noqa: S608
            params,
        ).fetchall()
    finally:
        conn.close()

    data = [_row_to_dict(r) for r in rows]
    if as_json:
        out.output_json({"success": True, "tasks": data, "count": len(data)})
    else:
        if not data:
            out.console.print("[dim]No tasks found.[/dim]")
        else:
            out.print_tasks_table(data)


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


@task.command("add")
@click.option("--project", "proj", required=True, help="Project id or name.")
@click.option("--title", required=True, help="Task title.")
@click.option("--desc", default="", help="Task description.")
@click.option("--priority", default="P2", help="Priority: P0/P1/P2/P3 (default P2).")
@click.option("--assignee", default="", help="Assignee.")
@click.option("--due", "due_date", default="", help="Due date (ISO 8601).")
@json_option
@click.pass_context
def task_add(
    ctx: click.Context,
    proj: str,
    title: str,
    desc: str,
    priority: str,
    assignee: str,
    due_date: str,
    as_json: bool,
) -> None:
    """Create a new task."""
    as_json = get_json_flag(ctx, as_json)
    conn = _db.get_db()
    try:
        project_row = _resolve_project(conn, proj)
        if not project_row:
            conn.close()
            if as_json:
                out.error_json(f"Project not found: {proj}")
            else:
                out.print_error(f"Project not found: {proj}")
            return

        task_id = make_id("task")
        ts = now()
        conn.execute(
            """
            INSERT INTO tasks
                (id, project_id, title, description, status, priority, assignee, due_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'todo', ?, ?, ?, ?, ?)
            """,
            (task_id, project_row["id"], title, desc, priority, assignee, due_date, ts, ts),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    finally:
        conn.close()

    data = _row_to_dict(row)
    if as_json:
        out.output_json({"success": True, "task": data})
    else:
        out.print_success(f"Task [bold]{title}[/bold] created ({task_id})")


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------


@task.command("show")
@click.argument("task_id")
@json_option
@click.pass_context
def task_show(ctx: click.Context, task_id: str, as_json: bool) -> None:
    """Show task details."""
    as_json = get_json_flag(ctx, as_json)
    conn = _db.get_db()
    try:
        row = _resolve_task(conn, task_id)
    finally:
        conn.close()

    if not row:
        if as_json:
            out.error_json(f"Task not found: {task_id}")
        else:
            out.print_error(f"Task not found: {task_id}")
        return

    data = _row_to_dict(row)
    if as_json:
        out.output_json({"success": True, "task": data})
    else:
        out.print_task_panel(data)


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


@task.command("update")
@click.argument("task_id")
@click.option("--title", default=None)
@click.option("--desc", default=None)
@click.option("--status", default=None)
@click.option("--priority", default=None)
@click.option("--assignee", default=None)
@click.option("--due", "due_date", default=None)
@json_option
@click.pass_context
def task_update(
    ctx: click.Context,
    task_id: str,
    title: str | None,
    desc: str | None,
    status: str | None,
    priority: str | None,
    assignee: str | None,
    due_date: str | None,
    as_json: bool,
) -> None:
    """Update task fields."""
    as_json = get_json_flag(ctx, as_json)

    fields: dict[str, str] = {}
    if title is not None:
        fields["title"] = title
    if desc is not None:
        fields["description"] = desc
    if status is not None:
        fields["status"] = status
    if priority is not None:
        fields["priority"] = priority
    if assignee is not None:
        fields["assignee"] = assignee
    if due_date is not None:
        fields["due_date"] = due_date

    if not fields:
        if as_json:
            out.error_json("No fields to update.")
        else:
            out.print_error("No fields to update.")
        return

    conn = _db.get_db()
    try:
        row = _resolve_task(conn, task_id)
        if not row:
            conn.close()
            if as_json:
                out.error_json(f"Task not found: {task_id}")
            else:
                out.print_error(f"Task not found: {task_id}")
            return

        fields["updated_at"] = str(now())
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [task_id]
        conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)  # noqa: S608
        updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    finally:
        conn.close()

    data = _row_to_dict(updated)
    if as_json:
        out.output_json({"success": True, "task": data})
    else:
        out.print_success(f"Task [bold]{row['title']}[/bold] updated.")


# ---------------------------------------------------------------------------
# done
# ---------------------------------------------------------------------------


@task.command("done")
@click.argument("task_id")
@json_option
@click.pass_context
def task_done(ctx: click.Context, task_id: str, as_json: bool) -> None:
    """Mark a task as done."""
    as_json = get_json_flag(ctx, as_json)
    conn = _db.get_db()
    try:
        row = _resolve_task(conn, task_id)
        if not row:
            conn.close()
            if as_json:
                out.error_json(f"Task not found: {task_id}")
            else:
                out.print_error(f"Task not found: {task_id}")
            return
        conn.execute(
            "UPDATE tasks SET status = 'done', updated_at = ? WHERE id = ?",
            (now(), task_id),
        )
    finally:
        conn.close()

    if as_json:
        out.output_json({"success": True, "task_id": task_id, "status": "done"})
    else:
        out.print_success(f"Task [bold]{row['title']}[/bold] marked as done.")


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


@task.command("delete")
@click.argument("task_id")
@click.option("--yes", is_flag=True, default=False, help="Skip confirmation.")
@json_option
@click.pass_context
def task_delete(ctx: click.Context, task_id: str, yes: bool, as_json: bool) -> None:
    """Delete a task."""
    as_json = get_json_flag(ctx, as_json)
    conn = _db.get_db()
    try:
        row = _resolve_task(conn, task_id)
        if not row:
            conn.close()
            if as_json:
                out.error_json(f"Task not found: {task_id}")
            else:
                out.print_error(f"Task not found: {task_id}")
            return

        if not yes and not as_json:
            click.confirm(f"Delete task '{row['title']}'?", abort=True)

        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    finally:
        conn.close()

    if as_json:
        out.output_json({"success": True, "deleted_id": task_id, "title": row["title"]})
    else:
        out.print_success(f"Task [bold]{row['title']}[/bold] deleted.")
