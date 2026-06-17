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
# A uid footnote the compiler will accept: exactly 10 alphanumerics. Must stay
# in sync with GUID_FOOTNOTE in app.logic.sources. A "[^uid]:" footnote whose
# value is any other shape is malformed and would fail the build.
_VALID_UID_RE = re.compile(rf"\[\^{settings.GUID_KEY}\]: *[A-Za-z0-9]{{10}} *$")

# A delimiter line: exactly "---" with optional trailing whitespace.
_SEP_LINE_RE = re.compile(r"^---[ \t]*$")
# A footnote line: "[^key]: value".
_FOOTNOTE_LINE_RE = re.compile(r"^\[\^\w+\]: *.+$")
# Card syntax: a ":::" Q/A separator or a "{{cN::" cloze. Text carrying it
# outside a well-formed block is an unfenced card; prose without it is left
# alone (matching the compiler, which ignores non-card prose).
_CARD_SYNTAX_RE = re.compile(r":::|\{\{ *c\d+ *::")


@dataclass
class StampResult:
    file: Path
    stamped_lines: List[int] = field(default_factory=list)
    skipped_reason: str = ""


@dataclass
class FixResult:
    file: Path
    changed: bool = False
    card_count: int = 0
    uids_added: int = 0
    skipped_reason: str = ""
    error: str = ""


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


class _FixError(ValueError):
    """A draft that ``ankc uid --fix`` cannot repair unambiguously."""


def _strip_blank_edges(text: str) -> str:
    """Drops leading/trailing blank lines, preserving internal ones."""
    lines = text.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def _is_footnote_region(text: str) -> bool:
    """True when every non-blank line is a ``[^key]: value`` footnote."""
    lines = [ln for ln in text.split("\n") if ln.strip()]
    return bool(lines) and all(_FOOTNOTE_LINE_RE.match(ln.strip()) for ln in lines)


def _split_body_and_footnotes(region: str) -> Tuple[str, List[str]]:
    """Splits a card region into its body and any trailing footnote lines.

    Footnotes normally sit in their own region after the closing ``---``, but a
    hand-written draft may glue them directly under the answer with no blank
    line; those would otherwise be absorbed into the card body.
    """
    lines = region.split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    footnotes: List[str] = []
    while lines and _FOOTNOTE_LINE_RE.match(lines[-1].strip()):
        footnotes.insert(0, lines.pop().strip())
    return _strip_blank_edges("\n".join(lines)), footnotes


def _has_unfenced_cards(work: str, body_start: int) -> bool:
    """True when card syntax appears outside every well-formed block.

    This is the only condition that warrants a structural rewrite. When false,
    the deck is already well-formed (any prose is intentionally ignored) and
    only uid stamping is needed.
    """
    cursor = body_start
    for match in _BLOCK_RE.finditer(work, body_start):
        if _CARD_SYNTAX_RE.search(work[cursor : match.start()]):
            return True
        end = match.end()
        following = _FOOTNOTES_RE.match(work, end)
        if following:
            end = following.end()
        cursor = max(cursor, end)
    return bool(_CARD_SYNTAX_RE.search(work[cursor:]))


def fix_text(raw: str) -> Tuple[str, int, int]:
    """Repairs a draft deck, returning ``(new_text, card_count, uids_added)``.

    When the deck is already well-formed (no card text sits outside a block),
    this delegates to ``stamp_text``: missing uids are appended and prose is
    left untouched, so it is safe and idempotent on canonical decks. When a
    draft has unfenced cards (cards separated by a single ``---``, or content
    before the first delimiter using the frontmatter's closing ``---`` as the
    opener), it rebuilds the body into canonical ``---`` / body / ``---`` /
    ``[^uid]`` blocks, preserving existing footnotes and dropping the obsolete
    trailing ``.`` sentinel.

    Raises ``_FixError`` for a draft it cannot repair unambiguously (a footnote
    block with no preceding card).

    Known limit: orphaned card *continuation* lines that carry no card syntax
    (no ``:::`` / cloze) are indistinguishable from intentional prose and are
    left to the compiler's own handling rather than rebuilt here.
    """
    work = raw if raw.endswith("\n") else raw + "\n"
    body_start = frontmatter_end_offset(work)
    frontmatter = work[:body_start]

    # Only restructure genuine decks (frontmatter with a 'deck:' key). Without
    # that signal a file might be an ordinary note that merely contains "::"; a
    # structural rewrite there would corrupt it. A non-deck file, or one already
    # well-formed, gets only append-only stamping, which is always safe.
    is_deck = bool(
        re.search(rf"(?m)^{re.escape(settings.DECK_TITLE_KEY)}:", frontmatter)
    )
    if not is_deck or not _has_unfenced_cards(work, body_start):
        new_text, lines = stamp_text(raw)
        card_count = sum(1 for _ in _BLOCK_RE.finditer(work, body_start))
        return new_text, card_count, len(lines)

    body = work[body_start:]

    # Drop a trailing legacy "." sentinel before splitting so it doesn't get
    # mistaken for card content.
    body = re.sub(r"\n[ \t]*\.[ \t]*\n*\Z", "\n", body)

    # Split the body on delimiter lines into regions.
    regions: List[str] = []
    current: List[str] = []
    for line in body.split("\n"):
        if _SEP_LINE_RE.match(line):
            regions.append("\n".join(current))
            current = []
        else:
            current.append(line)
    regions.append("\n".join(current))

    # Assemble card units: each body region plus any footnote region(s) that
    # immediately follow it. Content before the first delimiter is the first
    # card — the frontmatter's closing "---" serves as its opening delimiter,
    # so a draft needn't repeat it.
    units: List[Tuple[str, List[str]]] = []  # (body, footnote_lines)
    for region in regions:
        if not region.strip():
            continue
        if _is_footnote_region(region):
            if not units:
                raise _FixError("footnote block with no preceding card")
            units[-1][1].extend(ln.strip() for ln in region.split("\n") if ln.strip())
            continue
        body_text, trailing = _split_body_and_footnotes(region)
        if not body_text:
            # The region held only footnotes glued together; attach them.
            if not units:
                raise _FixError("footnote block with no preceding card")
            units[-1][1].extend(trailing)
            continue
        units.append((body_text, trailing))

    uids_added = 0
    rebuilt: List[str] = []
    for body_text, footnotes in units:
        # Drop malformed "[^uid]:" lines (a non-10-char value the compiler would
        # reject); a valid uid is generated below if none survives.
        footnotes = [
            ln
            for ln in footnotes
            if not (_UID_RE.search(ln) and not _VALID_UID_RE.match(ln))
        ]
        if not any(_VALID_UID_RE.match(ln) for ln in footnotes):
            uid = generate_random_string(length=10)
            footnotes.insert(0, f"[^{settings.GUID_KEY}]: {uid}")
            uids_added += 1
        footblock = "".join(f"{ln}\n" for ln in footnotes)
        rebuilt.append(f"---\n\n{body_text}\n\n---\n{footblock}")

    new_text = frontmatter + "\n".join(rebuilt)

    # Post-condition: the rebuild must leave no card outside a well-formed block.
    if _has_unfenced_cards(new_text, frontmatter_end_offset(new_text)):
        raise _FixError("could not rebuild into well-formed cards")

    return new_text, len(units), uids_added


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


def fix_file(path: Path, search_root: Path, dry_run: bool) -> FixResult:
    """Normalizes a single file (see ``fix_text``), writing atomically. Shares
    ``stamp_file``'s guards: skips symlinks, paths outside ``search_root``, and
    CRLF files. A draft that cannot be repaired is reported, not written."""
    if path.is_symlink():
        return FixResult(path, skipped_reason="symlink")

    resolved = path.resolve()
    if not resolved.is_relative_to(search_root.resolve()):
        return FixResult(path, skipped_reason="outside search path")

    if b"\r\n" in path.read_bytes():
        return FixResult(path, skipped_reason="CRLF line endings not supported")

    raw = read_file(path)
    try:
        new_text, card_count, uids_added = fix_text(raw)
    except _FixError as exc:
        return FixResult(path, error=str(exc))

    if new_text == raw:
        return FixResult(path, changed=False, card_count=card_count)

    # Post-condition: a second pass must be a no-op (output is canonical).
    again, _, _ = fix_text(new_text)
    if again != new_text:
        raise RuntimeError(f"fixing {path} did not converge; aborting write")

    if not dry_run:
        _atomic_write(path, raw, new_text)

    return FixResult(path, changed=True, card_count=card_count, uids_added=uids_added)


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
