from typing import Optional

import typer

from app.cli.build import build_app
from app.cli.list import list_app
from app.config import settings

app = typer.Typer()
app.add_typer(build_app, name="build")
app.add_typer(list_app, name="list")


@app.callback(invoke_without_command=True)
def default(
    version: Optional[bool] = typer.Option(
        False, "--version", help="Show version information"
    ),
) -> None:
    """Welcome to the AnkiPiler!"""
    if version:
        typer.echo(settings.VERSION)
