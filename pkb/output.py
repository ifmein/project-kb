"""Output helpers: JSON mode and rich human-readable rendering."""

from __future__ import annotations

import json
import sys
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
err_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def output_json(data: Any) -> None:
    """Print *data* as pretty JSON to stdout."""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def success_json(data: Any) -> None:
    """Wrap *data* in a ``{"success": true, ...}`` envelope and print."""
    output_json({"success": True, **data})


def error_json(message: str) -> None:
    """Print a ``{"success": false, "error": ...}`` JSON error and exit 1."""
    output_json({"success": False, "error": message})
    sys.exit(1)


# ---------------------------------------------------------------------------
# Rich human-readable output
# ---------------------------------------------------------------------------


def print_success(message: str) -> None:
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    err_console.print(f"[red]✗[/red] {message}")
    sys.exit(1)


def print_projects_table(rows: list[dict]) -> None:
    t = Table(box=box.SIMPLE_HEAD, show_edge=False)
    t.add_column("ID", style="dim", no_wrap=True)
    t.add_column("Name", style="bold")
    t.add_column("Status")
    t.add_column("Repo")
    t.add_column("Local Path")
    t.add_column("Tech Stack")
    t.add_column("Description")
    for r in rows:
        status_style = _status_style(r.get("status", ""))
        t.add_row(
            r.get("id", ""),
            r.get("name", ""),
            f"[{status_style}]{r.get('status', '')}[/{status_style}]",
            r.get("repo_url", "") or "",
            r.get("local_path", "") or "",
            r.get("tech_stack", "") or "",
            (r.get("description", "") or "")[:60],
        )
    console.print(t)


def print_project_panel(r: dict, task_stats: dict | None = None) -> None:
    lines = [
        f"[bold]ID:[/bold]          {r.get('id', '')}",
        f"[bold]Name:[/bold]        {r.get('name', '')}",
        f"[bold]Status:[/bold]      {r.get('status', '')}",
        f"[bold]Description:[/bold] {r.get('description', '')}",
        f"[bold]Repo:[/bold]        {r.get('repo_url', '') or '-'}",
        f"[bold]Local Path:[/bold]  {r.get('local_path', '') or '-'}",
        f"[bold]Tech Stack:[/bold]  {r.get('tech_stack', '') or '-'}",
        f"[bold]Created:[/bold]     {r.get('created_at', '')}",
        f"[bold]Updated:[/bold]     {r.get('updated_at', '')}",
    ]
    if task_stats:
        parts = ", ".join(f"{k}: {v}" for k, v in task_stats.items())
        lines.append(f"[bold]Tasks:[/bold]       {parts}")
    console.print(Panel("\n".join(lines), title=r.get("name", ""), expand=False))


def print_tasks_table(rows: list[dict]) -> None:
    t = Table(box=box.SIMPLE_HEAD, show_edge=False)
    t.add_column("ID", style="dim", no_wrap=True)
    t.add_column("Title", style="bold")
    t.add_column("Status")
    t.add_column("Priority")
    t.add_column("Due")
    for r in rows:
        st = r.get("status", "")
        style = _status_style(st)
        t.add_row(
            r.get("id", ""),
            r.get("title", ""),
            f"[{style}]{st}[/{style}]",
            r.get("priority", ""),
            r.get("due_date", "") or "",
        )
    console.print(t)


def print_task_panel(r: dict) -> None:
    lines = [
        f"[bold]ID:[/bold]          {r.get('id', '')}",
        f"[bold]Title:[/bold]       {r.get('title', '')}",
        f"[bold]Project:[/bold]     {r.get('project_id', '')}",
        f"[bold]Status:[/bold]      {r.get('status', '')}",
        f"[bold]Priority:[/bold]    {r.get('priority', '')}",
        f"[bold]Assignee:[/bold]    {r.get('assignee', '') or '-'}",
        f"[bold]Due:[/bold]         {r.get('due_date', '') or '-'}",
        f"[bold]Description:[/bold] {r.get('description', '') or '-'}",
        f"[bold]Created:[/bold]     {r.get('created_at', '')}",
    ]
    console.print(Panel("\n".join(lines), title=r.get("title", ""), expand=False))


def print_notes_table(rows: list[dict]) -> None:
    t = Table(box=box.SIMPLE_HEAD, show_edge=False)
    t.add_column("ID", style="dim", no_wrap=True)
    t.add_column("Content", style="bold")
    t.add_column("Tags")
    t.add_column("Project")
    t.add_column("Date")
    for r in rows:
        t.add_row(
            r.get("id", ""),
            (r.get("content", "") or "")[:60],
            r.get("tags", "") or "",
            r.get("project_id", "") or "-",
            r.get("created_at", ""),
        )
    console.print(t)


def print_note_panel(r: dict) -> None:
    lines = [
        f"[bold]ID:[/bold]      {r.get('id', '')}",
        f"[bold]Project:[/bold] {r.get('project_id', '') or '-'}",
        f"[bold]Tags:[/bold]    {r.get('tags', '') or '-'}",
        f"[bold]Created:[/bold] {r.get('created_at', '')}",
        "",
        r.get("content", ""),
    ]
    console.print(Panel("\n".join(lines), title="Note", expand=False))


def print_search_results(results: list[dict], query: str) -> None:
    if not results:
        console.print(f"[dim]No results for[/dim] [bold]{query!r}[/bold]")
        return
    console.print(f"[bold]{len(results)}[/bold] result(s) for [bold]{query!r}[/bold]\n")
    for r in results:
        rtype = r.get("type", "")
        if rtype == "project":
            title = f"[green]project[/green]  {r.get('id', '')}"
            body = (
                f"[bold]Name:[/bold]        {r.get('name', '')}\n"
                f"[bold]Description:[/bold] {r.get('description', '') or '-'}\n"
                f"[bold]Status:[/bold]      {r.get('status', '')}\n"
                f"[bold]Date:[/bold]        {r.get('created_at', '')}"
            )
        elif rtype == "note":
            title = f"[cyan]note[/cyan]  {r.get('id', '')}"
            body = (
                f"[bold]Content:[/bold] {r.get('content', '')}\n"
                f"[bold]Tags:[/bold]    {r.get('tags', '') or '-'}\n"
                f"[bold]Project:[/bold] {r.get('project', '') or '-'}\n"
                f"[bold]Date:[/bold]    {r.get('created_at', '')}"
            )
        else:
            title = f"[yellow]task[/yellow]  {r.get('id', '')}"
            body = (
                f"[bold]Title:[/bold]   {r.get('title', '')}\n"
                f"[bold]Status:[/bold]  {r.get('status', '')}  "
                f"[bold]Priority:[/bold] {r.get('priority', '')}\n"
                f"[bold]Project:[/bold] {r.get('project', '') or '-'}\n"
                f"[bold]Date:[/bold]    {r.get('created_at', '')}"
            )
        console.print(Panel(body, title=title, expand=False))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _status_style(status: str) -> str:
    return {
        "active": "green",
        "done": "green",
        "completed": "green",
        "in_progress": "yellow",
        "todo": "blue",
        "paused": "yellow",
        "cancelled": "dim",
        "archived": "dim",
    }.get(status, "white")
