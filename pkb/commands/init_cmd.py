"""Commands: pkb init / pkb status / pkb completion."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import click
from click.shell_completion import get_completion_class

from pkb import db as _db
from pkb import output as out
from pkb.options import get_json_flag, json_option

_CONFIG_DIR = Path.home() / ".config" / "project-kb"
# Path to the bundled libsimple inside the installed package (pkb/data/).
_BUNDLED_EXT = Path(__file__).parent.parent / "data" / "libsimple.dylib"


# ---------------------------------------------------------------------------
# pkb init
# ---------------------------------------------------------------------------


@click.command("init")
@json_option
@click.pass_context
def init_cmd(ctx: click.Context, as_json: bool) -> None:
    """Create ~/.config/project-kb/, initialise the DB, and load the simple tokenizer."""
    as_json = get_json_flag(ctx, as_json)

    # --- 1. Ensure config dir exists ---
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # --- 2. Copy libsimple.dylib if PKB_SIMPLE_EXT is not set ---
    ext_path = os.environ.get("PKB_SIMPLE_EXT", "")
    copied_ext = False
    if not ext_path:
        dest = _CONFIG_DIR / "libsimple.dylib"
        if not dest.exists() and _BUNDLED_EXT.exists():
            shutil.copy2(_BUNDLED_EXT, dest)
            copied_ext = True
        if dest.exists():
            # Set for this process so init_db picks it up
            ext_no_suffix = str(dest.with_suffix(""))
            os.environ["PKB_SIMPLE_EXT"] = ext_no_suffix
            ext_path = ext_no_suffix

    # --- 3. Initialise DB ---
    db_path = os.environ.get("PKB_DB_PATH", str(_CONFIG_DIR / "pkb.db"))
    conn = _db.get_db(db_path)
    tokenizer = _db.init_db(conn)
    conn.close()

    # --- 4. Report ---
    fish_snippet = (
        "# Add to ~/.config/fish/conf.d/pkb.fish :\n"
        f"set -x PKB_DIR {_CONFIG_DIR}\n"
        f"set -x PKB_DB_PATH $PKB_DIR/pkb.db\n"
        f"set -x PKB_SIMPLE_EXT $PKB_DIR/libsimple  # without extension"
    )

    info = {
        "db_path": db_path,
        "tokenizer": tokenizer,
        "ext_path": ext_path or None,
        "copied_ext": copied_ext,
        "fish_config": fish_snippet,
    }

    if as_json:
        out.output_json({"success": True, **info})
    else:
        out.print_success(f"DB initialised at [bold]{db_path}[/bold]")
        out.print_success(f"Tokenizer: [bold]{tokenizer}[/bold]")
        if copied_ext:
            out.print_success(f"Copied libsimple.dylib → {_CONFIG_DIR / 'libsimple.dylib'}")
        if ext_path:
            out.print_success(f"Extension path: {ext_path}")
        out.console.print(f"\n[dim]{fish_snippet}[/dim]")


# ---------------------------------------------------------------------------
# pkb status
# ---------------------------------------------------------------------------


@click.command("status")
@json_option
@click.pass_context
def status_cmd(ctx: click.Context, as_json: bool) -> None:
    """Show DB path, extension status, and row counts."""
    as_json = get_json_flag(ctx, as_json)

    db_path = os.environ.get("PKB_DB_PATH", str(_CONFIG_DIR / "pkb.db"))
    ext_path = os.environ.get("PKB_SIMPLE_EXT", "")

    conn = _db.get_db(db_path)
    ext_ok = _db.load_extension(conn)

    counts: dict[str, int] = {}
    for table in ("projects", "tasks", "notes"):
        try:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608
            counts[table] = row[0] if row else 0
        except Exception:
            counts[table] = -1
    conn.close()

    info = {
        "db_path": db_path,
        "ext_path": ext_path or None,
        "ext_loaded": ext_ok,
        "counts": counts,
    }

    if as_json:
        out.output_json({"success": True, **info})
    else:
        out.console.print(f"[bold]DB path:[/bold]    {db_path}")
        out.console.print(f"[bold]Extension:[/bold]  {ext_path or '(not set)'}")
        status_label = "[green]loaded[/green]" if ext_ok else "[yellow]not loaded (using unicode61)[/yellow]"
        out.console.print(f"[bold]Tokenizer:[/bold]  {status_label}")
        out.console.print()
        for table, count in counts.items():
            out.console.print(f"  {table:<12} {count} row(s)")


# ---------------------------------------------------------------------------
# pkb completion
# ---------------------------------------------------------------------------


@click.command("completion")
@click.argument("shell", type=click.Choice(["bash", "zsh"], case_sensitive=False))
@click.pass_context
def completion_cmd(ctx: click.Context, shell: str) -> None:
    """Print shell completion script for bash/zsh."""
    shell_name = shell.lower()
    complete_var = "_PKB_COMPLETE"
    shell_complete = get_completion_class(shell_name)
    if shell_complete is None:
        raise click.UsageError(f"Unsupported shell: {shell_name}")

    root_cmd = ctx.find_root().command
    script = shell_complete(
        cli=root_cmd,
        ctx_args={},
        prog_name="pkb",
        complete_var=complete_var,
    )
    click.echo(script.source())
