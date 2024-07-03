from pathlib import Path
from typing import List

from app.config import settings
from app.logic.sources import Source
from app.logic.utils import parse_markdown_file, search_markdown_files


def compile_source(
    source_name: str,
    source_search_path: Path,
    source_search_depth: int,
    output_path: Path,
) -> None:
    """Compiles a single source."""
    source = Source(
        name=source_name,
        search_path=source_search_path,
        search_depth=source_search_depth,
    )
    source.compile(output_path=output_path)


def compile_sources(
    source_names: List[str],
    source_search_path: Path,
    source_search_depth: int,
    output_path: Path,
) -> None:
    """Compiles a list of sources."""
    for source_name in source_names:
        compile_source(
            source_name=source_name,
            source_search_path=source_search_path,
            source_search_depth=source_search_depth,
            output_path=output_path,
        )


def list_source_names(
    decks_search_path: Path,
    decks_search_depth: int,
) -> List[str]:
    """Returns list of all sourceß names."""
    markdown_file_paths = search_markdown_files(
        search_dir=decks_search_path,
        search_depth=decks_search_depth,
    )

    deck_set = set()
    for file_path in markdown_file_paths:
        meta = parse_markdown_file(file_path)[0]

        deck_name = meta.get(settings.DECK_TITLE_KEY)

        if deck_name is not None:
            deck_set.add(deck_name)

    return list(deck_set)


def list_source_files(
    source_name: str,
    source_search_path: Path,
    source_search_depth: int,
) -> None:
    """Compiles a single source."""
    source = Source(
        name=source_name,
        search_path=source_search_path,
        search_depth=source_search_depth,
    )
    paths = source.get_source_file_paths()

    return paths
