from pathlib import Path
from typing import Annotated, Optional

import typer

from app.cli import DECK_HELP_STR, DEPTH_HELP_STR, PATH_HELP_STR
from app.logic.drivers import list_source_decks, list_source_files

list_app = typer.Typer()


@list_app.command("deck")
def list_src_decks(
    path: Annotated[Optional[Path], typer.Option(help=PATH_HELP_STR)] = Path("."),
    depth: Annotated[Optional[int], typer.Option(min=0, help=DEPTH_HELP_STR)] = 0,
) -> None:
    """Lists valid source decks."""

    search_path = path
    search_depth = depth

    source_names = list_source_decks(
        source_search_path=search_path, source_search_depth=search_depth
    )

    if len(source_names) == 0:
        typer.echo("No valid source decks found")
        raise typer.Exit(1)

    typer.echo(source_names)


@list_app.command("file")
def list_src_files(
    deck: Annotated[str, typer.Option(help=DECK_HELP_STR)],
    path: Annotated[Optional[Path], typer.Option(help=PATH_HELP_STR)] = Path("."),
    depth: Annotated[Optional[int], typer.Option(min=0, help=DEPTH_HELP_STR)] = 0,
) -> None:
    """Lists source files for a deck."""

    deck_name = deck
    search_path = path
    search_depth = depth

    source_names = list_source_files(
        deck_name=deck_name,
        source_search_path=search_path,
        source_search_depth=search_depth,
    )

    if len(source_names) == 0:
        typer.echo("No valid source files found")
        raise typer.Exit(1)

    typer.echo(source_names)
