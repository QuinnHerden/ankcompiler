import hashlib
from pathlib import Path
from typing import List


def search_files(extension: str, search_dir: Path, search_depth: int) -> List[Path]:
    """
    Looks for files with the given extension in
    the given directory and its subdirectories
    up to the specified search depth.
    """

    def search(current_dir: Path, current_depth: int) -> List[Path]:
        if current_depth > search_depth:
            return []

        result = []
        for item in current_dir.iterdir():
            if item.is_file() and item.suffix == f"{extension}":
                result.append(item)
            elif item.is_dir():
                result.extend(search(item, current_depth + 1))

        return result

    return search(search_dir, 0)


def get_markdown_files(search_dir: Path, search_depth: int) -> List[Path]:
    """Get all markdown files in
    the given directory and its subdirectories
    up to the specified search depth.
    """
    return search_files(".md", search_dir, search_depth)


def read_file(file: Path) -> str:
    """Get text from a file."""
    with file.open("r", encoding="utf-8") as f:
        text = f.read()

    return text


def integer_hash(text: str) -> int:
    """
    Convert a string into a random integer from 0 to 1<<31 exclusive.
    From https://stackoverflow.com/a/42089311/11499360
    """
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (1 << 31)
