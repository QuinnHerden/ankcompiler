from pathlib import Path
from typing import List, Optional

from app.config import settings
from app.logic.sources import Deck
from app.logic.utils import (
    generate_random_string,
    parse_markdown_file,
    search_markdown_files,
)
from app.logic.stamping import StampResult, file_is_dirty, stamp_file
from app.logic.validation import Finding, validate_files


def compile_deck(
    deck_name: str,
    source_search_path: Path,
    source_search_depth: Optional[int],
    output_path: Path,
) -> None:
    """Compiles a single deck."""
    source = Deck(
        name=deck_name,
        source_search_path=source_search_path,
        source_search_depth=source_search_depth,
    )
    source.compile(output_path=output_path)


def compile_decks(
    deck_names: List[str],
    source_search_path: Path,
    source_search_depth: Optional[int],
    output_path: Path,
) -> None:
    """Compiles a list of source decks."""
    for source_name in deck_names:
        compile_deck(
            deck_name=source_name,
            source_search_path=source_search_path,
            source_search_depth=source_search_depth,
            output_path=output_path,
        )


def list_source_decks(
    source_search_path: Path,
    source_search_depth: Optional[int],
) -> List[str]:
    """Returns list of all source deck names."""
    markdown_file_paths = search_markdown_files(
        search_path=source_search_path,
        search_depth=source_search_depth,
    )

    deck_set = set()
    for file_path in markdown_file_paths:
        meta = parse_markdown_file(file_path)[0]

        deck_name = meta.get(settings.DECK_TITLE_KEY)

        if deck_name is not None:
            deck_set.add(deck_name)

    return list(deck_set)


def list_source_files(
    deck_name: str,
    source_search_path: Path,
    source_search_depth: Optional[int],
) -> List[Path]:
    """Returns a list of all source file paths for a deck."""
    deck = Deck(
        name=deck_name,
        source_search_path=source_search_path,
        source_search_depth=source_search_depth,
    )
    paths = deck.get_source_file_paths()

    return paths


def validate_deck_files(
    deck_names: List[str],
    source_search_path: Path,
    source_search_depth: Optional[int],
) -> List[Finding]:
    """Validates all source files belonging to the given decks."""
    file_paths: List[Path] = []
    for deck_name in deck_names:
        file_paths.extend(
            list_source_files(
                deck_name=deck_name,
                source_search_path=source_search_path,
                source_search_depth=source_search_depth,
            )
        )

    return validate_files(file_paths)


def stamp_source_files(
    source_search_path: Path,
    source_search_depth: Optional[int],
    dry_run: bool,
) -> List[StampResult]:
    """Stamps missing uids across all markdown files under the search path."""
    files = search_markdown_files(
        search_path=source_search_path, search_depth=source_search_depth
    )
    return [
        stamp_file(path=path, search_root=source_search_path, dry_run=dry_run)
        for path in files
    ]


def dirty_source_files(
    source_search_path: Path,
    source_search_depth: Optional[int],
) -> List[Path]:
    """Returns markdown source files with uncommitted git changes."""
    files = search_markdown_files(
        search_path=source_search_path, search_depth=source_search_depth
    )
    return [path for path in files if file_is_dirty(path)]


def generate_chunk() -> str:
    """Returns an empty note chunk string."""
    uid = generate_random_string(length=10)
    return f"---\n---\n[^uid]: {uid}"
