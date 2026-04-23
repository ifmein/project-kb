"""CLI interface for Project Knowledge Base."""

import json
import sys
from datetime import datetime
from typing import Optional

import click

from db import Database
from models import Note, Project, Task
from search import format_timestamp, get_recent_items, search


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Project Knowledge Base (pkb) - CLI tool for agent project management."""
    pass


@main.group()
def project():
    """Manage projects."""
    pass


@project.command("list")
@click.option("--status", type=click.Choice(["active", "paused", "completed", "archived"]))
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def project_list(status, output_json):
    """List all projects."""
    db = Database()
    projects = db.list_projects(status)
    
    if output_json:
        data = []
        for p in projects:
            data.append({
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "status": p.status,
                "repo_url": p.repo_url,
                "tech_stack": p.tech_stack,
                "created_at": format_timestamp(p.created_at),
                "updated_at": format_timestamp(p.updated_at)
            })
        click.echo(json.dumps({"success": True, "projects": data, "count": len(data)}, indent=2))
    else:
        if not projects:
            click.echo("No projects found.")
            return
        
        for p in projects:
            click.echo(f"{p.id}: {p.name} [{p.status}]")
            if p.description:
                click.echo(f"  {p.description[:80]}...")
            click.echo(f"  Updated: {format_timestamp(p.updated_at)}")
            click.echo()


@project.command("add")
@click.option("--name", required=True, help="Project name (unique)")
@click.option("--desc", default="", help="Project description")
@click.option("--status", default="active", type=click.Choice(["active", "paused", "completed", "archived"]))
@click.option("--repo", default="", help="Repository URL")
@click.option("--tech", default="", help="Tech stack (comma-separated)")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def project_add(name, desc, status, repo, tech, output_json):
    """Add a new project."""
    db = Database()
    
    # Check if project already exists
    existing = db.get_project(name)
    if existing:
        click.echo(f"Error: Project '{name}' already exists.", err=True)
        sys.exit(1)
    
    project = Project.create(
        name=name,
        description=desc,
        status=status,
        repo_url=repo,
        tech_stack=tech
    )
    
    db.create_project(project)
    
    if output_json:
        data = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "repo_url": project.repo_url,
            "tech_stack": project.tech_stack,
            "created_at": format_timestamp(project.created_at),
            "updated_at": format_timestamp(project.updated_at)
        }
        click.echo(json.dumps({"success": True, "project": data}, indent=2))
    else:
        click.echo(f"Project created: {project.id} ({project.name})")


@project.command("show")
@click.argument("project_id")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def project_show(project_id, output_json):
    """Show project details and statistics."""
    db = Database()
    proj = db.get_project(project_id)
    
    if not proj:
        click.echo(f"Error: Project '{project_id}' not found.", err=True)
        sys.exit(1)
    
    # Get statistics
    tasks = db.list_tasks(project_id=proj.id)
    notes = db.list_notes(project_id=proj.id)
    
    task_stats = {
        "total": len(tasks),
        "todo": len([t for t in tasks if t.status == "todo"]),
        "in_progress": len([t for t in tasks if t.status == "in_progress"]),
        "done": len([t for t in tasks if t.status == "done"]),
        "cancelled": len([t for t in tasks if t.status == "cancelled"])
    }
    
    if output_json:
        data = {
            "id": proj.id,
            "name": proj.name,
            "description": proj.description,
            "status": proj.status,
            "repo_url": proj.repo_url,
            "tech_stack": proj.tech_stack,
            "created_at": format_timestamp(proj.created_at),
            "updated_at": format_timestamp(proj.updated_at),
            "statistics": {
                "tasks": task_stats,
                "notes": len(notes)
            }
        }
        click.echo(json.dumps({"success": True, "project": data}, indent=2))
    else:
        click.echo(f"Project: {proj.name}")
        click.echo(f"ID: {proj.id}")
        click.echo(f"Status: {proj.status}")
        if proj.description:
            click.echo(f"Description: {proj.description}")
        if proj.repo_url:
            click.echo(f"Repo: {proj.repo_url}")
        if proj.tech_stack:
            click.echo(f"Tech stack: {proj.tech_stack}")
        click.echo(f"Created: {format_timestamp(proj.created_at)}")
        click.echo(f"Updated: {format_timestamp(proj.updated_at)}")
        click.echo()
        click.echo("Statistics:")
        click.echo(f"  Tasks: {task_stats['total']} total, {task_stats['todo']} todo, {task_stats['in_progress']} in progress, {task_stats['done']} done")
        click.echo(f"  Notes: {len(notes)}")


@project.command("update")
@click.argument("project_id")
@click.option("--status", type=click.Choice(["active", "paused", "completed", "archived"]))
@click.option("--desc", help="Update description")
@click.option("--repo", help="Update repository URL")
@click.option("--tech", help="Update tech stack")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def project_update(project_id, status, desc, repo, tech, output_json):
    """Update project fields."""
    db = Database()
    
    updates = {}
    if status:
        updates["status"] = status
    if desc is not None:
        updates["description"] = desc
    if repo is not None:
        updates["repo_url"] = repo
    if tech is not None:
        updates["tech_stack"] = tech
    
    if not updates:
        click.echo("Error: No updates specified.", err=True)
        sys.exit(1)
    
    updated = db.update_project(project_id, **updates)
    
    if not updated:
        click.echo(f"Error: Project '{project_id}' not found.", err=True)
        sys.exit(1)
    
    if output_json:
        data = {
            "id": updated.id,
            "name": updated.name,
            "description": updated.description,
            "status": updated.status,
            "repo_url": updated.repo_url,
            "tech_stack": updated.tech_stack,
            "created_at": format_timestamp(updated.created_at),
            "updated_at": format_timestamp(updated.updated_at)
        }
        click.echo(json.dumps({"success": True, "project": data}, indent=2))
    else:
        click.echo(f"Project updated: {updated.id} ({updated.name})")


@project.command("delete")
@click.argument("project_id")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def project_delete(project_id, output_json):
    """Delete project (cascades to tasks and notes)."""
    db = Database()
    
    # Get project info before deletion
    proj = db.get_project(project_id)
    if not proj:
        click.echo(f"Error: Project '{project_id}' not found.", err=True)
        sys.exit(1)
    
    success = db.delete_project(project_id)
    
    if output_json:
        click.echo(json.dumps({"success": success, "deleted": project_id}, indent=2))
    else:
        if success:
            click.echo(f"Project deleted: {proj.name}")
        else:
            click.echo(f"Error: Failed to delete project '{project_id}'.", err=True)
            sys.exit(1)


@main.group()
def task():
    """Manage tasks."""
    pass


@task.command("list")
@click.option("--project", required=True, help="Project ID or name")
@click.option("--status", type=click.Choice(["todo", "in_progress", "done", "cancelled"]))
@click.option("--priority", type=click.Choice(["P0", "P1", "P2", "P3"]))
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def task_list(project, status, priority, output_json):
    """List tasks for a project."""
    db = Database()
    
    # Resolve project ID
    proj = db.get_project(project)
    if not proj:
        click.echo(f"Error: Project '{project}' not found.", err=True)
        sys.exit(1)
    
    tasks = db.list_tasks(project_id=proj.id, status=status, priority=priority)
    
    if output_json:
        data = []
        for t in tasks:
            data.append({
                "id": t.id,
                "project_id": t.project_id,
                "title": t.title,
                "description": t.description,
                "status": t.status,
                "priority": t.priority,
                "assignee": t.assignee,
                "due_date": t.due_date,
                "created_at": format_timestamp(t.created_at),
                "updated_at": format_timestamp(t.updated_at)
            })
        click.echo(json.dumps({"success": True, "tasks": data, "count": len(data)}, indent=2))
    else:
        if not tasks:
            click.echo("No tasks found.")
            return
        
        for t in tasks:
            status_icon = {"todo": "○", "in_progress": "◐", "done": "●", "cancelled": "✗"}.get(t.status, "?")
            priority_icon = {"P0": "🔥", "P1": "❗", "P2": "📌", "P3": "📎"}.get(t.priority, "")
            click.echo(f"{status_icon} {t.id}: {t.title} {priority_icon}")
            if t.description:
                click.echo(f"  {t.description[:60]}...")
            if t.due_date:
                click.echo(f"  Due: {t.due_date}")
            click.echo()


@task.command("add")
@click.option("--project", required=True, help="Project ID or name")
@click.option("--title", required=True, help="Task title")
@click.option("--desc", default="", help="Task description")
@click.option("--priority", default="P2", type=click.Choice(["P0", "P1", "P2", "P3"]))
@click.option("--assignee", default="", help="Assignee")
@click.option("--due", help="Due date (ISO 8601)")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def task_add(project, title, desc, priority, assignee, due, output_json):
    """Add a new task to a project."""
    db = Database()
    
    # Resolve project ID
    proj = db.get_project(project)
    if not proj:
        click.echo(f"Error: Project '{project}' not found.", err=True)
        sys.exit(1)
    
    task = Task.create(
        project_id=proj.id,
        title=title,
        description=desc,
        priority=priority,
        assignee=assignee,
        due_date=due
    )
    
    db.create_task(task)
    
    if output_json:
        data = {
            "id": task.id,
            "project_id": task.project_id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "assignee": task.assignee,
            "due_date": task.due_date,
            "created_at": format_timestamp(task.created_at),
            "updated_at": format_timestamp(task.updated_at)
        }
        click.echo(json.dumps({"success": True, "task": data}, indent=2))
    else:
        click.echo(f"Task created: {task.id} ({task.title})")


@task.command("show")
@click.argument("task_id")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def task_show(task_id, output_json):
    """Show task details."""
    db = Database()
    t = db.get_task(task_id)
    
    if not t:
        click.echo(f"Error: Task '{task_id}' not found.", err=True)
        sys.exit(1)
    
    if output_json:
        data = {
            "id": t.id,
            "project_id": t.project_id,
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "priority": t.priority,
            "assignee": t.assignee,
            "due_date": t.due_date,
            "created_at": format_timestamp(t.created_at),
            "updated_at": format_timestamp(t.updated_at)
        }
        click.echo(json.dumps({"success": True, "task": data}, indent=2))
    else:
        click.echo(f"Task: {t.title}")
        click.echo(f"ID: {t.id}")
        click.echo(f"Project: {t.project_id}")
        click.echo(f"Status: {t.status}")
        click.echo(f"Priority: {t.priority}")
        if t.assignee:
            click.echo(f"Assignee: {t.assignee}")
        if t.due_date:
            click.echo(f"Due: {t.due_date}")
        if t.description:
            click.echo(f"Description: {t.description}")
        click.echo(f"Created: {format_timestamp(t.created_at)}")
        click.echo(f"Updated: {format_timestamp(t.updated_at)}")


@task.command("update")
@click.argument("task_id")
@click.option("--status", type=click.Choice(["todo", "in_progress", "done", "cancelled"]))
@click.option("--priority", type=click.Choice(["P0", "P1", "P2", "P3"]))
@click.option("--desc", help="Update description")
@click.option("--assignee", help="Update assignee")
@click.option("--due", help="Update due date")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def task_update(task_id, status, priority, desc, assignee, due, output_json):
    """Update task fields."""
    db = Database()
    
    updates = {}
    if status:
        updates["status"] = status
    if priority:
        updates["priority"] = priority
    if desc is not None:
        updates["description"] = desc
    if assignee is not None:
        updates["assignee"] = assignee
    if due is not None:
        updates["due_date"] = due
    
    if not updates:
        click.echo("Error: No updates specified.", err=True)
        sys.exit(1)
    
    updated = db.update_task(task_id, **updates)
    
    if not updated:
        click.echo(f"Error: Task '{task_id}' not found.", err=True)
        sys.exit(1)
    
    if output_json:
        data = {
            "id": updated.id,
            "project_id": updated.project_id,
            "title": updated.title,
            "description": updated.description,
            "status": updated.status,
            "priority": updated.priority,
            "assignee": updated.assignee,
            "due_date": updated.due_date,
            "created_at": format_timestamp(updated.created_at),
            "updated_at": format_timestamp(updated.updated_at)
        }
        click.echo(json.dumps({"success": True, "task": data}, indent=2))
    else:
        click.echo(f"Task updated: {updated.id} ({updated.title})")


@task.command("done")
@click.argument("task_id")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def task_done(task_id, output_json):
    """Mark task as done (shortcut for update --status done)."""
    db = Database()
    updated = db.update_task(task_id, status="done")
    
    if not updated:
        click.echo(f"Error: Task '{task_id}' not found.", err=True)
        sys.exit(1)
    
    if output_json:
        data = {
            "id": updated.id,
            "title": updated.title,
            "status": updated.status
        }
        click.echo(json.dumps({"success": True, "task": data}, indent=2))
    else:
        click.echo(f"Task marked as done: {updated.title}")


@task.command("delete")
@click.argument("task_id")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def task_delete(task_id, output_json):
    """Delete task."""
    db = Database()
    
    # Get task info before deletion
    t = db.get_task(task_id)
    if not t:
        click.echo(f"Error: Task '{task_id}' not found.", err=True)
        sys.exit(1)
    
    success = db.delete_task(task_id)
    
    if output_json:
        click.echo(json.dumps({"success": success, "deleted": task_id}, indent=2))
    else:
        if success:
            click.echo(f"Task deleted: {t.title}")
        else:
            click.echo(f"Error: Failed to delete task '{task_id}'.", err=True)
            sys.exit(1)


@main.group()
def note():
    """Manage notes."""
    pass


@note.command("add")
@click.argument("content")
@click.option("--project", help="Project ID or name (optional for global notes)")
@click.option("--tags", default="", help="Tags (comma-separated)")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def note_add(content, project, tags, output_json):
    """Add a new note."""
    db = Database()
    
    project_id = None
    if project:
        proj = db.get_project(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found.", err=True)
            sys.exit(1)
        project_id = proj.id
    
    note = Note.create(
        content=content,
        project_id=project_id,
        tags=tags
    )
    
    db.create_note(note)
    
    if output_json:
        data = {
            "id": note.id,
            "project_id": note.project_id,
            "content": note.content,
            "tags": note.tags,
            "created_at": format_timestamp(note.created_at)
        }
        click.echo(json.dumps({"success": True, "note": data}, indent=2))
    else:
        click.echo(f"Note created: {note.id}")
        if project_id:
            click.echo(f"Project: {project_id}")


@note.command("list")
@click.option("--project", help="Project ID or name")
@click.option("--limit", default=10, help="Limit number of results")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def note_list(project, limit, output_json):
    """List notes."""
    db = Database()
    
    project_id = None
    if project:
        proj = db.get_project(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found.", err=True)
            sys.exit(1)
        project_id = proj.id
    
    notes = db.list_notes(project_id=project_id, limit=limit)
    
    if output_json:
        data = []
        for n in notes:
            data.append({
                "id": n.id,
                "project_id": n.project_id,
                "content": n.content,
                "tags": n.tags,
                "created_at": format_timestamp(n.created_at)
            })
        click.echo(json.dumps({"success": True, "notes": data, "count": len(data)}, indent=2))
    else:
        if not notes:
            click.echo("No notes found.")
            return
        
        for n in notes:
            click.echo(f"{n.id}: {n.content[:60]}...")
            if n.project_id:
                click.echo(f"  Project: {n.project_id}")
            if n.tags:
                click.echo(f"  Tags: {n.tags}")
            click.echo(f"  Created: {format_timestamp(n.created_at)}")
            click.echo()


@note.command("show")
@click.argument("note_id")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def note_show(note_id, output_json):
    """Show note details."""
    db = Database()
    n = db.get_note(note_id)
    
    if not n:
        click.echo(f"Error: Note '{note_id}' not found.", err=True)
        sys.exit(1)
    
    if output_json:
        data = {
            "id": n.id,
            "project_id": n.project_id,
            "content": n.content,
            "tags": n.tags,
            "created_at": format_timestamp(n.created_at)
        }
        click.echo(json.dumps({"success": True, "note": data}, indent=2))
    else:
        click.echo(f"Note: {n.id}")
        if n.project_id:
            click.echo(f"Project: {n.project_id}")
        click.echo(f"Content: {n.content}")
        if n.tags:
            click.echo(f"Tags: {n.tags}")
        click.echo(f"Created: {format_timestamp(n.created_at)}")


@note.command("delete")
@click.argument("note_id")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def note_delete(note_id, output_json):
    """Delete note."""
    db = Database()
    
    # Get note info before deletion
    n = db.get_note(note_id)
    if not n:
        click.echo(f"Error: Note '{note_id}' not found.", err=True)
        sys.exit(1)
    
    success = db.delete_note(note_id)
    
    if output_json:
        click.echo(json.dumps({"success": success, "deleted": note_id}, indent=2))
    else:
        if success:
            click.echo(f"Note deleted: {n.content[:30]}...")
        else:
            click.echo(f"Error: Failed to delete note '{note_id}'.", err=True)
            sys.exit(1)


@main.command(name="search")
@click.argument("query", required=False)
@click.option("--project", help="Limit search to project")
@click.option("--type", "search_type", type=click.Choice(["project", "task", "note"]), help="Limit search type")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def search_cmd(query, project, search_type, output_json):
    """Search across projects, tasks, and notes."""
    db = Database()
    
    # Resolve project ID if provided
    project_id = None
    if project:
        proj = db.get_project(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found.", err=True)
            sys.exit(1)
        project_id = proj.id
    
    if query:
        # Perform search
        results = search(query, project_id, search_type, db)
    else:
        # No query - return recent items (like session_search)
        results = get_recent_items(db=db)
    
    if output_json:
        click.echo(json.dumps(results, indent=2))
    else:
        if not results["results"]:
            click.echo("No results found.")
            return
        
        click.echo(f"Found {results['count']} results:")
        click.echo()
        
        for item in results["results"]:
            item_type = item.get('type', 'unknown')
            if item_type == 'project':
                click.echo(f"[Project] {item['name']}")
                if item.get('description'):
                    click.echo(f"  {item['description'][:60]}...")
            elif item_type == 'task':
                click.echo(f"[Task] {item['title']}")
                if item.get('description'):
                    click.echo(f"  {item['description'][:60]}...")
                click.echo(f"  Status: {item.get('status', 'unknown')}, Priority: {item.get('priority', 'unknown')}")
            elif item_type == 'note':
                click.echo(f"[Note] {item['content'][:60]}...")
                if item.get('tags'):
                    click.echo(f"  Tags: {item['tags']}")
            click.echo(f"  Created: {item.get('created_at', 'unknown')}")
            click.echo()


if __name__ == "__main__":
    main()