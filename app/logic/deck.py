import re
from pathlib import Path
from typing import List

from genanki.deck import Deck
from genanki.note import Note
from genanki.package import Package

from app.config import settings
from app.logic.parser import parse_note_block, split_markdown_file, split_markdown_page
from app.logic.utils import generate_integer_hash, get_markdown_files


def list_source_decks(
    decks_search_path: Path,
    decks_search_depth: int,
) -> List[str]:
    """Returns list of all source deck names."""
    markdown_files = get_markdown_files(
        search_dir=decks_search_path,
        search_depth=decks_search_depth,
    )

    deck_set = set()
    for file in markdown_files:
        frontmatter = split_markdown_file(file)[0]
        deck_name = frontmatter.get(settings.DECK_TITLE_KEY)
        if deck_name is not None:
            deck_set.add(deck_name)

    return list(deck_set)


def get_source_deck_paths(
    deck_name: str,
    decks_search_path: Path,
    decks_search_depth: int,
) -> List[Path]:
    """Returns list of all source deck paths of passed name."""
    markdown_files = get_markdown_files(
        search_dir=decks_search_path,
        search_depth=decks_search_depth,
    )

    deck_paths = []
    for md_path in markdown_files:
        frontmatter = split_markdown_file(md_path)[0]
        md_deck_name = frontmatter.get(settings.DECK_TITLE_KEY)
        if md_deck_name == deck_name:
            deck_paths.append(md_path)

    return deck_paths


def compile_decks(
    deck_names: List[str],
    deck_search_path: Path,
    deck_search_depth: int,
) -> None:
    """Compiles each passed deck."""
    for deck in deck_names:
        compile_deck(deck, deck_search_path, deck_search_depth)


def get_notes(file_path) -> List[Note]:
    """Returns a list of notes from the passed deck file path."""
    contents = split_markdown_file(file_path)[1]
    note_blocks = split_markdown_page(contents)

    notes = []
    for block in note_blocks:
        notes.append(parse_note_block(block))

    return notes


def compile_deck(
    deck_name: str,
    deck_search_path: Path,
    deck_search_depth: int,
) -> None:
    """Packages a deck from a source deck."""
    deck = create_deck(deck_name)

    source_file_paths = get_source_deck_paths(
        deck_name, deck_search_path, deck_search_depth
    )

    notes = []
    for source_path in source_file_paths:
        notes.extend(get_notes(source_path))

    for note in notes:
        deck.add_note(note)

    cleaned_deck_name = clean_deck_name(deck_name)
    Package(deck).write_to_file(f"{cleaned_deck_name}.apkg")


def create_deck(deck_name: str) -> Deck:
    """Creates a GenAnki Deck."""
    return Deck(deck_id=generate_integer_hash(deck_name), name=deck_name)


def clean_deck_name(deck_name: str) -> str:
    """Cleans a deck name for use in filenames and the like."""
    return re.sub("[^a-zA-Z0-9]", "-", deck_name).lower()
