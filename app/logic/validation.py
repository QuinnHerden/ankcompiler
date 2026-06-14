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

# Anything that looks like a card opener: a "---" line followed by a blank line.
_OPENER_RE = re.compile(r"(?m)^---\n\s*\n")


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

    findings.extend(_check_unparsed_openers(body, body_start, raw, matched_spans, path))

    return findings


def _validate_chunk(
    chunk: Chunk, path: Path, line: int, seen_uids: Dict[str, Tuple[Path, int]]
) -> List[Finding]:
    findings: List[Finding] = []
    meta = chunk._extract_meta()

    uid = meta.get(settings.GUID_KEY)
    if uid is None:
        snippet = chunk.body.strip().splitlines()[0][:50]
        findings.append(
            Finding(path, line, "error", f'card block missing uid — "{snippet}"')
        )
    elif uid in seen_uids:
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

    # Type resolution + field extraction reuse the production logic; surface
    # their errors as findings with location instead of aborting.
    try:
        note_type = chunk._resolve_type(meta)
        chunk._extract_md_fields(note_type)
    except ValueError as exc:
        findings.append(Finding(path, line, "error", str(exc)))

    return findings


def _check_unparsed_openers(
    body: str,
    body_start: int,
    raw: str,
    matched_spans: List[Tuple[int, int]],
    path: Path,
) -> List[Finding]:
    """Flags card-like openers that no well-formed block consumed."""
    findings: List[Finding] = []
    for opener in _OPENER_RE.finditer(body):
        inside = any(start <= opener.start() < end for start, end in matched_spans)
        if not inside:
            line = line_at(raw, body_start + opener.start())
            # Heuristic (a stray "---" in prose can trip it), so warn rather
            # than error — this must not block an otherwise valid build.
            findings.append(
                Finding(
                    path,
                    line,
                    "warning",
                    "possibly malformed or unterminated card block",
                )
            )
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
