import hashlib
import logging
import re
import secrets
import string
from pathlib import Path
from typing import List, Optional, Tuple

import frontmatter
from markdown import markdown
from yaml.constructor import ConstructorError


def search_files(
    extension: str, search_dir: Path, search_depth: Optional[int] = None
) -> List[Path]:
    """
    Looks for files with the given extension in the given directory and its
    subdirectories. When ``search_depth`` is None all subdirectories are
    searched; otherwise the search is limited to that many levels below the
    root (depth 0 = root only).

    Hidden directories (names starting with ".") and symlinked directories are
    skipped, the latter to avoid symlink-cycle infinite recursion. Directories
    that cannot be read are logged and skipped.
    """

    def search(current_dir: Path, current_depth: int) -> List[Path]:
        if search_depth is not None and current_depth > search_depth:
            return []

        try:
            items = list(current_dir.iterdir())
        except OSError as exc:
            logging.warning("Could not read directory %s: %s", current_dir, exc)
            return []

        result = []
        for item in items:
            if item.is_file() and item.suffix == f"{extension}":
                result.append(item)
            elif (
                item.is_dir()
                and not item.is_symlink()
                and not item.name.startswith(".")
            ):
                result.extend(search(item, current_depth + 1))

        return result

    return search(search_dir, 0)


def search_markdown_files(
    search_path: Path, search_depth: Optional[int] = None
) -> List[Path]:
    """Get all markdown files in the given directory and its subdirectories,
    limited to ``search_depth`` levels when provided (None = unlimited).
    """
    return search_files(".md", search_path, search_depth)


def read_file(file: Path) -> str:
    """Get text from a file."""
    with file.open("r", encoding="utf-8") as f:
        text = f.read()

    return text


def parse_markdown_file(file_path: Path) -> Tuple[dict, str]:
    """Parse a markdown file into metadata and body.

    The returned body is guaranteed to be newline-terminated when non-empty.
    The chunk-extraction regexes depend on trailing newlines, so a document
    ending on a card block with no trailing newline would otherwise drop its
    last card (issue #25).
    """
    try:
        split = frontmatter.parse(read_file(file_path))
    except ConstructorError:
        logging.warning("Could not parse file: %s", file_path)
        split = ({}, "")

    meta = split[0]
    body = split[1]

    if body and not body.endswith("\n"):
        body += "\n"

    return meta, body


def generate_integer_hash(text: str) -> int:
    """Generate an integer hash value for the given input string."""
    sha256_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

    hash_value = 0
    for i in range(0, 40, 2):
        byte = int(sha256_hash[i : i + 2], 16)
        for _ in range(4):
            if (byte & 1) == 1:
                hash_value += 1 << ((3 - _) * 8)
            byte >>= 1

    return hash_value


def generate_random_string(length: int = 10) -> str:
    """Generate a random alphanumeric string (A-Z, a-z, 0-9) of the given length."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_url_regex_expression() -> str:
    """Returns the regex expression for URLs."""

    return (
        r"\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+"
        r"|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))"
        r"*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    )


def clean_str_for_filename(text: str) -> str:
    """Cleans a string for use in filenames."""
    return re.sub("[^a-zA-Z0-9]", "-", text).lower()


def convert_md_to_html(md_fields: List[str]) -> List[str]:
    """
    Converts markdown text fields to HTML fields.
    """
    html_fields = []
    for field in md_fields:
        md_field = markdown(
            field,
            extensions=["fenced_code", "tables", "pymdownx.arithmatex"],
            # generic mode emits \(...\) / \[...\] (data only, no inline
            # script), which Anki's built-in MathJax renders.
            extension_configs={"pymdownx.arithmatex": {"generic": True}},
        )
        html_fields.append(md_field)

    return html_fields
