from typing import List, Optional

import typer

from app.logic.drivers import deck_family
from app.logic.utils import normalize_deck_name

DECK_HELP_STR = "Specify the name of the source deck"

PATH_HELP_STR = "Declare the base directory to search for valid source decks"
DEPTH_HELP_STR = (
    "Limit how many subdirectory levels to search (default: all subdirectories)"
)


def select_decks(all_: bool, deck: Optional[str], source_names: List[str]) -> List[str]:
    """Resolves --all / --deck to the source decks they cover, exiting on an
    invalid selection. ``--deck`` covers the deck and its subdecks."""
    if all_ and deck is not None:
        typer.echo("Use either --deck or --all, not both.")
        raise typer.Exit(1)
    if all_:
        return source_names
    if deck is not None:
        family = deck_family(normalize_deck_name(deck), source_names)
        if family:
            return family
    typer.echo("Not a valid source selection.")
    raise typer.Exit(1)
