import base64
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
