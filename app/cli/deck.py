from pathlib import Path
from typing import Annotated, Optional

import typer

from app.logic.deck import compile_deck, compile_decks, list_source_decks

deck_app = typer.Typer()

PATH_HELP_STR = "Declare the base directory to search for valid decks"
DEPTH_HELP_STR = "Declare the maximum search depth for valid decks"


@deck_app.command("list")
def list_src_decks(
    path: Annotated[Optional[Path], typer.Option(help=PATH_HELP_STR)] = None,
    depth: Annotated[Optional[int], typer.Option(min=0, help=DEPTH_HELP_STR)] = None,
) -> None:
    """Lists valid source decks."""

    if path:
        search_path = Path(path)
    else:
        search_path = Path.cwd()

    if depth:
        search_depth = depth
    else:
        search_depth = 0

    dirs = list_source_decks(
        decks_search_path=search_path, decks_search_depth=search_depth
    )

    if len(dirs) == 0:
        typer.echo("No valid source decks found")
        raise typer.Exit(1)

    typer.echo(dirs)


@deck_app.command("compile")
def compile_src_decks(
    all_: Annotated[
        Optional[bool],
        typer.Option("--all", help="Compile every deck"),
    ] = False,
    name: Annotated[Optional[str], typer.Option(help="Compile explicit deck")] = None,
    path: Annotated[
        Optional[Path],
        typer.Option(help=PATH_HELP_STR),
    ] = None,
    depth: Annotated[
        Optional[int],
        typer.Option(min=0, help=DEPTH_HELP_STR),
    ] = None,
) -> None:
    """Compiles valid source deck(s) into Anki package(s)."""

    if path:
        search_path = Path(path)
    else:
        search_path = Path.cwd()

    if depth:
        search_depth = depth
    else:
        search_depth = 0

    decks = list_source_decks(
        decks_search_path=search_path, decks_search_depth=search_depth
    )

    if all_ is False and name in decks:
        compile_deck(
            deck_name=name,
            deck_search_path=search_path,
            deck_search_depth=search_depth,
        )

    elif all_ is True:
        compile_decks(
            deck_names=decks,
            deck_search_path=search_path,
            deck_search_depth=search_depth,
        )

    else:
        typer.echo("Not a valid deck selection.")
        raise typer.Exit(1)
