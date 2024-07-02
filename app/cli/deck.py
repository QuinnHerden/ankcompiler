from pathlib import Path
from typing import Annotated, Optional

import typer

from app.logic.drivers import compile_source, compile_sources, list_source_names

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

    source_names = list_source_names(
        decks_search_path=search_path, decks_search_depth=search_depth
    )

    if len(source_names) == 0:
        typer.echo("No valid source decks found")
        raise typer.Exit(1)

    typer.echo(source_names)


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
    output: Annotated[
        Optional[Path],
        typer.Option(help="Declare the output directory to write compiled packes to"),
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

    if output:
        output_path = Path(output)
    else:
        output_path = Path.cwd()

    source_names = list_source_names(
        decks_search_path=search_path, decks_search_depth=search_depth
    )

    if all_ is False and name in source_names:
        compile_source(
            source_name=name,
            source_search_path=search_path,
            source_search_depth=search_depth,
            output_path=output_path,
        )

    elif all_ is True:
        compile_sources(
            source_names=source_names,
            source_search_path=search_path,
            source_search_depth=search_depth,
            output_path=output_path,
        )

    else:
        typer.echo("Not a valid deck selection.")
        raise typer.Exit(1)
