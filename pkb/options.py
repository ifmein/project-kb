"""Shared Click option decorators."""

from __future__ import annotations

import click


def json_option(f):
    """Add a ``--json`` flag to a Click command (usable at any position)."""
    return click.option(
        "--json",
        "as_json",
        is_flag=True,
        default=False,
        help="Output as JSON.",
    )(f)


def get_json_flag(ctx: click.Context, local_as_json: bool) -> bool:
    """Return True if JSON output is requested (local flag OR parent group flag)."""
    parent_json = (ctx.obj or {}).get("json", False)
    return local_as_json or parent_json
