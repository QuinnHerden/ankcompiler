from pathlib import Path
from typing import Annotated, Optional

import typer

from app.cli import DEPTH_HELP_STR, PATH_HELP_STR, select_decks
from app.logic.drivers import (
    compile_deck,
    compile_decks,
    list_source_decks,
    package_name_collisions,
    root_decks,
    validate_deck_files,
)
from app.logic.utils import normalize_deck_name
from app.logic.validation import format_findings

build_app = typer.Typer()


def _abort_on_validation_errors(deck_names, search_path, search_depth) -> None:
    """Validate before compiling so problems surface with file/line context
    instead of an opaque mid-compile traceback."""
    findings = validate_deck_files(
        deck_names=deck_names,
        source_search_path=search_path,
        source_search_depth=search_depth,
    )
    if findings:
        typer.echo(format_findings(findings))
    if any(f.level == "error" for f in findings):
        raise typer.Exit(1)


@build_app.callback(invoke_without_command=True)
def compile_src_decks(
    all_: Annotated[
        Optional[bool],
        typer.Option(
            "--all", help="Compile every deck, one package per top-level deck"
        ),
    ] = False,
    deck: Annotated[
        Optional[str], typer.Option(help="Compile explicit deck and its subdecks")
    ] = None,
    path: Annotated[
        Optional[Path],
        typer.Option(help=PATH_HELP_STR),
    ] = Path("."),
    depth: Annotated[
        Optional[int],
        typer.Option(min=0, help=DEPTH_HELP_STR),
    ] = None,
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

    deck_names = select_decks(all_, deck, source_names)
    _abort_on_validation_errors(deck_names, search_path, search_depth)

    if all_:
        collisions = package_name_collisions(root_decks(source_names))
        if collisions:
            for names in collisions:
                typer.echo(f"Decks {names} would write the same package file.")
            raise typer.Exit(1)
        compile_decks(
            source_names=source_names,
            source_search_path=search_path,
            source_search_depth=search_depth,
            output_path=output_path,
        )
    else:
        compile_deck(
            deck_name=normalize_deck_name(deck),
            deck_names=deck_names,
            source_search_path=search_path,
            source_search_depth=search_depth,
            output_path=output_path,
        )
