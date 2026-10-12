from pathlib import Path
from typing import Dict, List, Optional

from app.config import settings
from app.logic.sources import Deck, compile_package
from app.logic.utils import (
    clean_str_for_filename,
    generate_random_string,
    normalize_deck_name,
    parse_markdown_file,
    search_markdown_files,
)
from app.logic.stamping import (
    FixResult,
    StampResult,
    file_is_dirty,
    fix_file,
    stamp_file,
)
from app.logic.validation import Finding, validate_files


def deck_family(deck_name: str, source_names: List[str]) -> List[str]:
    """Returns the deck and its subdecks (``deck_name::...``) among the source
    decks."""
    prefix = f"{deck_name}::"
    return sorted(
        name for name in source_names if name == deck_name or name.startswith(prefix)
    )


def root_decks(source_names: List[str]) -> List[str]:
    """Returns the top-level deck names, one per deck hierarchy."""
    return sorted({name.split("::")[0] for name in source_names})


def compile_deck(
    deck_name: str,
    deck_names: List[str],
    source_search_path: Path,
    source_search_depth: Optional[int],
    output_path: Path,
) -> None:
    """Compiles a deck family (``deck_names``) into a single package named after
    ``deck_name``."""
    decks = [
        Deck(
            name=name,
            source_search_path=source_search_path,
            source_search_depth=source_search_depth,
        )
        for name in deck_names
    ]
    compile_package(name=deck_name, decks=decks, output_path=output_path)


def compile_decks(
    source_names: List[str],
    source_search_path: Path,
    source_search_depth: Optional[int],
    output_path: Path,
) -> None:
    """Compiles one package per top-level deck."""
    for root in root_decks(source_names):
        compile_deck(
            deck_name=root,
            deck_names=deck_family(root, source_names),
            source_search_path=source_search_path,
            source_search_depth=source_search_depth,
            output_path=output_path,
        )


def package_name_collisions(deck_names: List[str]) -> List[List[str]]:
    """Returns groups of deck names that would write the same package file."""
    by_file_name: Dict[str, List[str]] = {}
    for name in deck_names:
        by_file_name.setdefault(clean_str_for_filename(name), []).append(name)
    return [names for names in by_file_name.values() if len(names) > 1]


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

        deck_name = normalize_deck_name(meta.get(settings.DECK_TITLE_KEY))

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


def fix_source_files(
    source_search_path: Path,
    source_search_depth: Optional[int],
    dry_run: bool,
) -> List[FixResult]:
    """Normalizes draft card blocks across all markdown files under the search
    path, expanding single-``---``-separated cards and stamping missing uids."""
    files = search_markdown_files(
        search_path=source_search_path, search_depth=source_search_depth
    )
    return [
        fix_file(path=path, search_root=source_search_path, dry_run=dry_run)
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
