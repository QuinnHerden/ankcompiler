from pathlib import Path
from typing import Annotated, Optional

import typer

from app.cli import DEPTH_HELP_STR, PATH_HELP_STR
from app.logic.drivers import compile_deck, compile_decks, list_source_decks

build_app = typer.Typer()


@build_app.callback(invoke_without_command=True)
def compile_src_decks(
    all_: Annotated[
        Optional[bool],
        typer.Option("--all", help="Compile every deck"),
    ] = False,
    deck: Annotated[Optional[str], typer.Option(help="Compile explicit deck")] = None,
    path: Annotated[
        Optional[Path],
        typer.Option(help=PATH_HELP_STR),
    ] = Path("."),
    depth: Annotated[
        Optional[int],
        typer.Option(min=0, help=DEPTH_HELP_STR),
    ] = 0,
    output: Annotated[
        Optional[Path],
        typer.Option(help="Declare the output directory to write compiled packages to"),
    ] = Path("."),
) -> None:
    """Compiles valid deck(s) into Anki package(s)."""

    search_path = path
    search_depth = depth
    output_path = output

    source_names = list_source_decks(
        source_search_path=search_path, source_search_depth=search_depth
    )

    if all_ is False and deck in source_names:
        compile_deck(
            deck_name=deck,
            source_search_path=search_path,
            source_search_depth=search_depth,
            output_path=output_path,
        )

    elif all_ is True:
        compile_decks(
            deck_names=source_names,
            source_search_path=search_path,
            source_search_depth=search_depth,
            output_path=output_path,
        )

    else:
        typer.echo("Not a valid source selection.")
        raise typer.Exit(1)
