from typing import Optional

import typer

from app.cli.deck import deck_app
from app.config import settings

app = typer.Typer()
app.add_typer(deck_app, name="deck")


@app.callback(invoke_without_command=True)
def default(
    version: Optional[bool] = typer.Option(
        False, "--version", help="Show version information"
    ),
) -> None:
    """Welcome to the AnkiPiler!"""
    if version:
        typer.echo(settings.VERSION)
