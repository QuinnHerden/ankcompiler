from pathlib import Path
from typing import Annotated, Optional

import typer

from app.cli import DEPTH_HELP_STR, PATH_HELP_STR
from app.logic.drivers import dirty_source_files, stamp_source_files

uid_app = typer.Typer()


@uid_app.callback(invoke_without_command=True)
def stamp_uids(
    path: Annotated[Optional[Path], typer.Option(help=PATH_HELP_STR)] = Path("."),
    depth: Annotated[Optional[int], typer.Option(min=0, help=DEPTH_HELP_STR)] = None,
    check: Annotated[
        bool,
        typer.Option("--check", help="Report what would be stamped; write nothing"),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Stamp even if files have uncommitted changes"),
    ] = False,
) -> None:
    """Inserts a [^uid] footnote into any card block that lacks one."""

    # Refuse to rewrite files with uncommitted changes so there's always a
    # clean git checkpoint to revert to. --check writes nothing; --force opts out.
    if not check and not force:
        dirty = dirty_source_files(source_search_path=path, source_search_depth=depth)
        if dirty:
            typer.echo("Refusing to stamp files with uncommitted changes:")
            for dirty_path in dirty:
                typer.echo(f"  {dirty_path}")
            typer.echo("Commit or stash them first, or pass --force.")
            raise typer.Exit(1)

    results = stamp_source_files(
        source_search_path=path, source_search_depth=depth, dry_run=check
    )

    total = 0
    for result in results:
        if result.stamped_lines:
            count = len(result.stamped_lines)
            total += count
            verb = "would stamp" if check else "stamped"
            lines = ", ".join(str(line) for line in result.stamped_lines)
            typer.echo(f"{result.file}: {verb} {count} uid(s) at line(s) {lines}")

    if total == 0:
        typer.echo("nothing to stamp — all card blocks have uids")
    else:
        typer.echo(f"{total} uid(s) {'would be ' if check else ''}added")

    if check and total > 0:
        raise typer.Exit(1)
