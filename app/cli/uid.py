from pathlib import Path
from typing import Annotated, Optional

import typer

from app.cli import DEPTH_HELP_STR, PATH_HELP_STR
from app.logic.drivers import (
    dirty_source_files,
    fix_source_files,
    stamp_source_files,
)

uid_app = typer.Typer()


@uid_app.callback(invoke_without_command=True)
def stamp_uids(
    path: Annotated[Optional[Path], typer.Option(help=PATH_HELP_STR)] = Path("."),
    depth: Annotated[Optional[int], typer.Option(min=0, help=DEPTH_HELP_STR)] = None,
    check: Annotated[
        bool,
        typer.Option("--check", help="Report what would change; write nothing"),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Run even if files have uncommitted changes"),
    ] = False,
    fix: Annotated[
        bool,
        typer.Option(
            "--fix",
            help="Repair drafts: expand single-'---'-separated cards into "
            "well-formed blocks and stamp missing uids (rewrites structure)",
        ),
    ] = False,
) -> None:
    """Inserts a [^uid] footnote into any card block that lacks one.

    By default this is append-only and never alters card structure. Pass
    --fix to additionally normalize a draft whose cards are separated by a
    single '---' delimiter into well-formed card blocks.
    """

    # Refuse to rewrite files with uncommitted changes so there's always a
    # clean git checkpoint to revert to. --check writes nothing; --force opts out.
    if not check and not force:
        dirty = dirty_source_files(source_search_path=path, source_search_depth=depth)
        if dirty:
            typer.echo("Refusing to modify files with uncommitted changes:")
            for dirty_path in dirty:
                typer.echo(f"  {dirty_path}")
            typer.echo("Commit or stash them first, or pass --force.")
            raise typer.Exit(1)

    if fix:
        _run_fix(path=path, depth=depth, check=check)
        return

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


def _run_fix(path: Optional[Path], depth: Optional[int], check: bool) -> None:
    """Handles `ankc uid --fix`: structural normalization of draft decks."""
    results = fix_source_files(
        source_search_path=path, source_search_depth=depth, dry_run=check
    )

    changed = 0
    uids = 0
    had_error = False
    for result in results:
        if result.error:
            had_error = True
            typer.echo(f"{result.file}: cannot fix — {result.error}")
        elif result.changed:
            changed += 1
            uids += result.uids_added
            verb = "would reformat" if check else "reformatted"
            typer.echo(
                f"{result.file}: {verb} {result.card_count} card(s), "
                f"{result.uids_added} uid(s) added"
            )

    if had_error:
        raise typer.Exit(1)

    if changed == 0:
        typer.echo("nothing to fix — all decks are well-formed")
    else:
        verb = "would be " if check else ""
        typer.echo(f"{changed} file(s) {verb}reformatted, {uids} uid(s) added")

    if check and changed > 0:
        raise typer.Exit(1)
