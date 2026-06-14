import json
from pathlib import Path
from typing import Annotated, List, Optional

import typer

from app.cli import DEPTH_HELP_STR, PATH_HELP_STR
from app.logic.drivers import list_source_decks, validate_deck_files
from app.logic.validation import findings_to_dicts, format_findings

check_app = typer.Typer()


@check_app.callback(invoke_without_command=True)
def check_src_decks(
    all_: Annotated[
        Optional[bool],
        typer.Option("--all", help="Check every deck"),
    ] = False,
    deck: Annotated[Optional[str], typer.Option(help="Check an explicit deck")] = None,
    path: Annotated[Optional[Path], typer.Option(help=PATH_HELP_STR)] = Path("."),
    depth: Annotated[Optional[int], typer.Option(min=0, help=DEPTH_HELP_STR)] = None,
    format_: Annotated[
        str,
        typer.Option("--format", help="Output format: text or json"),
    ] = "text",
) -> None:
    """Validates deck source files without compiling them."""

    if all_:
        deck_names: List[str] = list_source_decks(
            source_search_path=path, source_search_depth=depth
        )
    elif deck is not None:
        deck_names = [deck]
    else:
        typer.echo("Not a valid source selection.")
        raise typer.Exit(1)

    findings = validate_deck_files(
        deck_names=deck_names,
        source_search_path=path,
        source_search_depth=depth,
    )

    if format_ == "json":
        typer.echo(json.dumps(findings_to_dicts(findings), indent=2))
    else:
        typer.echo(format_findings(findings))

    if any(finding.level == "error" for finding in findings):
        raise typer.Exit(1)
