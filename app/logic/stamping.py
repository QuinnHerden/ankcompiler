import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from app.config import settings
from app.logic.sources import NOTE_BODY
from app.logic.utils import (
    frontmatter_end_offset,
    generate_random_string,
    line_at,
    read_file,
)

# A card block whose closing "---" is followed by a newline. We deliberately
# do not reuse the combined chunk regex: stamping operates on raw file text
# (frontmatter intact) and only needs the block boundary, not the metadata.
_BLOCK_RE = re.compile(rf"---\n\s*\n+{NOTE_BODY}\n\s*\n---\n")
# Contiguous footnote lines immediately following a block.
_FOOTNOTES_RE = re.compile(r"(?:\[\^\w+\]: *.+?\n)*")
_UID_RE = re.compile(rf"\[\^{settings.GUID_KEY}\]:")


@dataclass
class StampResult:
    file: Path
    stamped_lines: List[int] = field(default_factory=list)
    skipped_reason: str = ""


def stamp_text(raw: str) -> Tuple[str, List[int]]:
    """Inserts a ``[^uid]`` footnote after every card block that lacks one.

    Returns the new text and the 1-based line numbers of the inserted
    footnotes. Pure and idempotent: blocks that already have a uid are left
    untouched, and a file needing no stamps is returned byte-for-byte.
    """
    # Normalize a trailing newline for matching (mirrors parse_markdown_file,
    # #25) so a block ending the file without one is still seen. The original
    # is returned unchanged when nothing is stamped, so clean files are intact.
    work = raw if raw.endswith("\n") else raw + "\n"
    body_start = frontmatter_end_offset(work)
    result = work[:body_start]
    cursor = body_start
    stamped_lines: List[int] = []

    for match in _BLOCK_RE.finditer(work, body_start):
        result += work[cursor : match.end()]
        cursor = match.end()

        following = _FOOTNOTES_RE.match(work, cursor)
        footnotes = following.group(0) if following else ""

        if not _UID_RE.search(footnotes):
            uid = generate_random_string(length=10)
            result += f"[^{settings.GUID_KEY}]: {uid}\n"
            stamped_lines.append(line_at(work, cursor))  # the inserted footnote

    result += work[cursor:]

    if not stamped_lines:
        return raw, []
    return result, stamped_lines


def stamp_file(path: Path, search_root: Path, dry_run: bool) -> StampResult:
    """Stamps a single file, writing atomically. Skips symlinks and any path
    that resolves outside ``search_root``."""
    if path.is_symlink():
        return StampResult(path, skipped_reason="symlink")

    resolved = path.resolve()
    if not resolved.is_relative_to(search_root.resolve()):
        return StampResult(path, skipped_reason="outside search path")

    # read_file translates CRLF -> LF; rewriting such a file would convert
    # every line ending, not just the stamped lines. Skip rather than mangle.
    if b"\r\n" in path.read_bytes():
        return StampResult(path, skipped_reason="CRLF line endings not supported")

    raw = read_file(path)
    new_text, stamped_lines = stamp_text(raw)

    if not stamped_lines:
        return StampResult(path)

    # Post-condition: a second pass must be a no-op (every block now has a uid).
    _, again = stamp_text(new_text)
    if again:
        raise RuntimeError(f"stamping {path} did not converge; aborting write")

    if not dry_run:
        _atomic_write(path, raw, new_text)

    return StampResult(path, stamped_lines=stamped_lines)


def file_is_dirty(path: Path) -> Optional[bool]:
    """Returns True if ``path`` has uncommitted git changes, False if clean,
    or None if git is unavailable or the file isn't in a git repository."""
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "--", str(path)],
            capture_output=True,
            text=True,
            cwd=path.parent,
        )
    except (FileNotFoundError, OSError):
        return None

    if proc.returncode != 0:
        return None

    return bool(proc.stdout.strip())


def _atomic_write(path: Path, original: str, new_text: str) -> None:
    """Writes ``new_text`` to ``path`` via a temp file + atomic rename,
    preserving the file mode and line endings. Aborts if the file changed
    on disk since it was read."""
    if read_file(path) != original:
        raise RuntimeError(f"{path} changed on disk during stamping; aborting write")

    directory = path.parent
    fd, tmp_name = tempfile.mkstemp(dir=directory, suffix=".ankc-tmp")
    tmp_path = Path(tmp_name)
    try:
        # newline="" writes without translation; CRLF files are rejected
        # upstream, so the text is LF and is written verbatim.
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(new_text)
        shutil.copystat(path, tmp_path)
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
