import base64
import hashlib
import logging
import re
from pathlib import Path
from typing import List, Tuple

import frontmatter
from markdown import markdown
from yaml.constructor import ConstructorError


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


def search_markdown_files(search_path: Path, search_depth: int) -> List[Path]:
    """Get all markdown files in
    the given directory and its subdirectories
    up to the specified search depth.
    """
    return search_files(".md", search_path, search_depth)


def read_file(file: Path) -> str:
    """Get text from a file."""
    with file.open("r", encoding="utf-8") as f:
        text = f.read()

    return text


def parse_markdown_file(file_path: Path) -> Tuple[dict, str]:
    """Parse a markdown file into metadata and body."""
    try:
        split = frontmatter.parse(read_file(file_path))
    except ConstructorError:
        logging.warning("Could not parse file: %s", file_path)
        split = ({}, "")

    meta = split[0]
    body = split[1]

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


def generate_string_hash(text: str) -> str:
    """Generate a 10-character truncated SHA-256 hash."""
    hash_object = hashlib.sha256(text.encode())
    hash_base64 = base64.urlsafe_b64encode(hash_object.digest())
    hash_value = hash_base64[:10].decode()
    print(type(hash_value))

    return hash_value


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
        md_field = markdown(field, extensions=["markdown.extensions.fenced_code"])
        html_fields.append(md_field)

    return html_fields
