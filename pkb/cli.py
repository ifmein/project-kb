"""pkb — Project Knowledge Base CLI entry point."""

from __future__ import annotations

import click

from pkb.commands.init_cmd import completion_cmd, init_cmd, status_cmd
from pkb.commands.note import note
from pkb.commands.project import project
from pkb.commands.search import search
from pkb.commands.task import task


@click.group()
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
@click.pass_context
def cli(ctx: click.Context, as_json: bool) -> None:
    """pkb — project knowledge base for agents and humans."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = as_json


cli.add_command(init_cmd, name="init")
cli.add_command(status_cmd, name="status")
cli.add_command(completion_cmd, name="completion")
cli.add_command(project)
cli.add_command(task)
cli.add_command(note)
cli.add_command(search)
