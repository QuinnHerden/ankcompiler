import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.logic.sources import (
    GUID_FOOTNOTE,
    NOTE_BODY,
    TAG_FOOTNOTE,
    TYPE_FOOTNOTE,
    Chunk,
    File,
)
from app.logic.utils import (
    frontmatter_end_offset,
    line_at,
    parse_markdown_file,
    read_file,
)

# Same block grammar as File.extract_chunks (shared sub-patterns), but with
# named groups and finditer so we can report line numbers.
_NOTE = rf"(?:---\n\s*\n+(?P<body>{NOTE_BODY})\n\s*\n---\n+)"
_META = rf"(?P<meta>(?:{GUID_FOOTNOTE}|{TAG_FOOTNOTE}|{TYPE_FOOTNOTE})*)"
_BLOCK_RE = re.compile(_NOTE + _META)

# A footnote line ("[^uid]: ...") is benign outside a matched block.
_FOOTNOTE_LINE_RE = re.compile(r"^\[\^\w+\]:")
# Card syntax: a "::: " Q/A separator or a "{{cN::" cloze. Its presence outside
# a matched block means a card was meant there but won't compile. Prose without
# it is intentionally ignored (see examples/example.md), so it is not flagged.
_CARD_SYNTAX_RE = re.compile(r":::|\{\{ *c\d+ *::")


@dataclass
class Finding:
    file: Path
    line: Optional[int]
    level: str  # "error" | "warning"
    message: str

    def format(self) -> str:
        loc = f"{self.file}:{self.line}" if self.line else str(self.file)
        return f"{loc}: {self.level}: {self.message}"


def validate_files(file_paths: List[Path]) -> List[Finding]:
    """Validates the given source files, returning all findings (deck-wide:
    duplicate uids are detected across the whole set)."""
    findings: List[Finding] = []
    seen_uids: Dict[str, Tuple[Path, int]] = {}

    for path in file_paths:
        findings.extend(_validate_file(path, seen_uids))

    return findings


def _validate_file(path: Path, seen_uids: Dict[str, Tuple[Path, int]]) -> List[Finding]:
    findings: List[Finding] = []
    raw = read_file(path)
    meta, _ = parse_markdown_file(path)

    if meta.get(settings.DECK_TITLE_KEY) is None:
        findings.append(
            Finding(path, 1, "error", "frontmatter is missing a 'deck' key")
        )

    body_start = frontmatter_end_offset(raw)
    body = raw[body_start:]
    # Match parse_markdown_file's trailing-newline normalization (#25) so a
    # document ending on a card block isn't seen as missing its footnotes.
    if body and not body.endswith("\n"):
        body += "\n"
    file_obj = File(path=path, meta=meta, body=body)

    matched_spans: List[Tuple[int, int]] = []
    for match in _BLOCK_RE.finditer(body):
        matched_spans.append((match.start(), match.end()))
        line = line_at(raw, body_start + match.start())
        chunk = Chunk(body=match.group("body"), meta=match.group("meta"), file=file_obj)
        findings.extend(_validate_chunk(chunk, path, line, seen_uids))

    findings.extend(_check_dropped_content(body, body_start, raw, matched_spans, path))

    return findings


def _validate_chunk(
    chunk: Chunk, path: Path, line: int, seen_uids: Dict[str, Tuple[Path, int]]
) -> List[Finding]:
    findings: List[Finding] = []

    # Chunk-level validity (missing uid, note type) comes from the chunk
    # itself; this function adds location and the deck-level duplicate check.
    for message in chunk.validate():
        findings.append(Finding(path, line, "error", message))

    uid = chunk.uid
    if uid is not None:
        if uid in seen_uids:
            prev_file, prev_line = seen_uids[uid]
            findings.append(
                Finding(
                    path,
                    line,
                    "error",
                    f"duplicate uid '{uid}' (first seen at {prev_file}:{prev_line})",
                )
            )
        else:
            seen_uids[uid] = (path, line)

    return findings


def _check_dropped_content(
    body: str,
    body_start: int,
    raw: str,
    matched_spans: List[Tuple[int, int]],
    path: Path,
) -> List[Finding]:
    """Flags card-like text that falls outside every well-formed block.

    The compiler only emits notes for text the block grammar matches, and prose
    outside a block is intentionally ignored (see examples/example.md). But text
    carrying card syntax ("::" Q/A or a cloze) outside a block is a card that
    won't compile — usually two cards sharing a single "---" (so the second has
    no opening delimiter), an unterminated block, or a draft whose cards aren't
    fenced. That would be silently dropped, so it is reported as an error and the
    build aborts. Run `ankc uid --fix` to repair a draft.
    """
    findings: List[Finding] = []

    # Compute the gaps in the body not covered by any matched block span.
    gaps: List[Tuple[int, int]] = []
    cursor = 0
    for start, end in sorted(matched_spans):
        if start > cursor:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < len(body):
        gaps.append((cursor, len(body)))

    for gap_start, gap_end in gaps:
        segment = body[gap_start:gap_end]
        if not _CARD_SYNTAX_RE.search(segment):
            continue  # blanks, delimiters, footnotes, or ignored prose

        # Point at the first non-structural line in the gap.
        offset = gap_start
        for line in segment.splitlines(keepends=True):
            stripped = line.strip()
            if stripped and stripped != "---" and not _FOOTNOTE_LINE_RE.match(stripped):
                findings.append(
                    Finding(
                        path,
                        line_at(raw, body_start + offset),
                        "error",
                        "malformed or unterminated card block — this content is "
                        "not inside a well-formed card and would be silently "
                        "dropped (run `ankc uid --fix` to repair a draft)",
                    )
                )
                break  # one finding per gap is enough to flag the defect
            offset += len(line)
    return findings


def format_findings(findings: List[Finding]) -> str:
    """Renders findings as compiler-style lines plus a summary footer."""
    lines = [f.format() for f in findings]
    errors = sum(1 for f in findings if f.level == "error")
    warnings = sum(1 for f in findings if f.level == "warning")
    files = len({f.file for f in findings})

    if not findings:
        lines.append("no problems found")
    else:
        summary = f"{errors} error(s), {warnings} warning(s) across {files} file(s)"
        lines.append(summary)

    return "\n".join(lines)


def findings_to_dicts(findings: List[Finding]) -> List[dict]:
    """Machine-readable form of findings (for --format json)."""
    return [
        {
            "file": str(f.file),
            "line": f.line,
            "level": f.level,
            "message": f.message,
        }
        for f in findings
    ]
