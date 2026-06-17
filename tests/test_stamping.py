import re
import subprocess

from app.logic.stamping import fix_file, fix_text, stamp_file, stamp_text
from app.logic.validation import validate_files

DECK = (
    "---\ndeck: foo\n---\n"
    "---\n\nq1 ::: a1\n\n---\n[^uid]: abc1234567\n\n"  # already has uid
    "---\n\nq2 ::: a2\n\n---\n[^tag]: x\n\n"  # tag only, needs uid
    "---\n\nq3 ::: a3\n\n---\n"  # no footnotes, needs uid
)

_UID_LINE = re.compile(r"^\[\^uid\]: [A-Za-z0-9]{10}$", re.MULTILINE)


class TestStampText:
    def test_stamps_only_blocks_without_uid(self):
        new_text, lines = stamp_text(DECK)
        assert len(lines) == 2
        assert len(_UID_LINE.findall(new_text)) == 3  # 1 existing + 2 added

    def test_existing_uid_untouched(self):
        new_text, _ = stamp_text(DECK)
        assert "abc1234567" in new_text

    def test_uid_inserted_before_existing_tag(self):
        new_text, _ = stamp_text(DECK)
        # the stamped uid for q2 comes immediately before its [^tag]
        assert re.search(r"\[\^uid\]: [A-Za-z0-9]{10}\n\[\^tag\]: x", new_text)

    def test_idempotent(self):
        once, _ = stamp_text(DECK)
        twice, lines = stamp_text(once)
        assert lines == []
        assert twice == once

    def test_no_card_blocks_is_noop(self):
        text = "---\ndeck: foo\n---\njust prose, no blocks\n"
        new_text, lines = stamp_text(text)
        assert lines == []
        assert new_text == text

    def test_clean_file_returned_byte_for_byte(self):
        # no trailing newline, already has uid -> must be returned unchanged
        text = "---\ndeck: foo\n---\n---\n\nq ::: a\n\n---\n[^uid]: abc1234567"
        new_text, lines = stamp_text(text)
        assert lines == []
        assert new_text == text

    def test_stamps_block_at_eof_without_trailing_newline(self):
        text = "---\ndeck: foo\n---\n---\n\nq ::: a\n\n---"
        new_text, lines = stamp_text(text)
        assert len(lines) == 1
        assert _UID_LINE.search(new_text)


class TestStampFile:
    def test_writes_atomically_and_preserves_unrelated_content(self, tmp_path):
        path = tmp_path / "deck.md"
        path.write_text(DECK)
        result = stamp_file(path, tmp_path, dry_run=False)
        assert len(result.stamped_lines) == 2
        assert len(_UID_LINE.findall(path.read_text())) == 3

    def test_dry_run_does_not_write(self, tmp_path):
        path = tmp_path / "deck.md"
        path.write_text(DECK)
        before = path.read_text()
        result = stamp_file(path, tmp_path, dry_run=True)
        assert result.stamped_lines  # reports work
        assert path.read_text() == before  # but writes nothing

    def test_preserves_file_mode(self, tmp_path):
        path = tmp_path / "deck.md"
        path.write_text(DECK)
        path.chmod(0o640)
        stamp_file(path, tmp_path, dry_run=False)
        assert (path.stat().st_mode & 0o777) == 0o640

    def test_symlink_skipped(self, tmp_path):
        real = tmp_path / "real.md"
        real.write_text(DECK)
        link = tmp_path / "link.md"
        link.symlink_to(real)
        result = stamp_file(link, tmp_path, dry_run=False)
        assert result.skipped_reason == "symlink"
        assert not result.stamped_lines

    def test_crlf_file_skipped_not_mangled(self, tmp_path):
        path = tmp_path / "deck.md"
        path.write_bytes(DECK.replace("\n", "\r\n").encode("utf-8"))
        before = path.read_bytes()
        result = stamp_file(path, tmp_path, dry_run=False)
        assert result.skipped_reason == "CRLF line endings not supported"
        assert path.read_bytes() == before  # untouched

    def test_clean_file_no_change(self, tmp_path):
        path = tmp_path / "deck.md"
        path.write_text(
            "---\ndeck: foo\n---\n---\n\nq ::: a\n\n---\n[^uid]: abc1234567\n"
        )
        result = stamp_file(path, tmp_path, dry_run=False)
        assert result.stamped_lines == []


CANONICAL = (
    "---\ndeck: foo\n---\n"
    "---\n\nq1 ::: a1\n\n---\n[^uid]: abc1234567\n"
    "\n---\n\nq2 ::: a2\n\n---\n[^uid]: def8901234\n"
)

# A draft: cards separated by a single "---", no uids, first card before the
# first delimiter, plus a trailing legacy "." sentinel.
DRAFT = "---\ndeck: foo\n---\n" "\nq1 ::: a1\n\n---\n\nq2 ::: a2\n\n---\n\n.\n"


class TestFixText:
    def test_expands_single_dash_draft(self):
        new_text, cards, uids = fix_text(DRAFT)
        assert cards == 2
        assert uids == 2
        assert len(_UID_LINE.findall(new_text)) == 2
        # each card is now wrapped in its own pair of "---" fences
        assert new_text.count("---\n\nq1 ::: a1\n\n---") == 1
        assert new_text.count("---\n\nq2 ::: a2\n\n---") == 1

    def test_drops_legacy_sentinel(self):
        new_text, _, _ = fix_text(DRAFT)
        # the lone "." sentinel must not survive as content
        assert "\n.\n" not in new_text
        assert not new_text.rstrip().endswith(".")

    def test_idempotent_on_canonical(self):
        new_text, cards, uids = fix_text(CANONICAL)
        assert cards == 2
        assert uids == 0
        assert new_text == CANONICAL  # byte-for-byte

    def test_fix_output_is_a_fixed_point(self):
        once, _, _ = fix_text(DRAFT)
        twice, cards, uids = fix_text(once)
        assert twice == once
        assert uids == 0

    def test_preserves_existing_uid_and_tag(self):
        draft = (
            "---\ndeck: foo\n---\n" "\nq ::: a\n\n---\n[^uid]: keepthis01\n[^tag]: t\n"
        )
        new_text, _, uids = fix_text(draft)
        assert uids == 0
        assert "keepthis01" in new_text
        assert "[^tag]: t" in new_text

    def test_no_delimiters_is_noop(self):
        text = "---\ndeck: foo\n---\njust prose, no card blocks\n"
        new_text, cards, uids = fix_text(text)
        assert (cards, uids) == (0, 0)
        assert new_text == text

    def test_no_frontmatter_not_restructured(self):
        # a file without a deck: frontmatter is not a deck — never rebuilt
        # (rebuilding would let frontmatter parsing swallow the first card)
        draft = "q1 ::: a1\n\n---\n\nq2 ::: a2\n\n---\n"
        new_text, _, _ = fix_text(draft)
        assert "q1 ::: a1" in new_text  # content not destroyed
        assert not new_text.startswith("---\n\nq1")  # not turned into a block

    def test_malformed_existing_uid_regenerated(self):
        # an existing "[^uid]: short" is not a valid 10-char uid; the compiler
        # would reject it, so fix must replace it rather than report success
        draft = (
            "---\ndeck: foo\n---\n\nq1 ::: a1\n\n---\n[^uid]: short\n\n"
            "---\n\nq2 ::: a2\n\n---\n"
        )
        new_text, cards, uids = fix_text(draft)
        assert "short" not in new_text
        assert len(_UID_LINE.findall(new_text)) == 2  # both cards valid uids

    def test_glued_footnote_not_absorbed_into_body(self):
        # a footnote directly under the answer (no blank line) must be peeled
        # off, not absorbed into the card body or duplicated
        draft = (
            "---\ndeck: foo\n---\n\nq1 ::: a1\n[^uid]: keepthis01\n\n"
            "---\n\nq2 ::: a2\n\n---\n"
        )
        new_text, _, uids = fix_text(draft)
        assert uids == 1  # q1 keeps its uid; only q2 gets a new one
        assert "keepthis01" in new_text
        assert "a1\n[^uid]" not in new_text  # footnote not glued in the body

    def test_footnote_without_card_raises(self):
        from app.logic.stamping import _FixError

        # a draft (unfenced q2 triggers the rebuild) whose first region is a
        # footnote with no preceding card — unrepairable
        bad = (
            "---\ndeck: foo\n---\n[^uid]: orphan0001\n\n"
            "---\n\nq1 ::: a1\n\n---\n\nq2 ::: a2\n\n---\n"
        )
        try:
            fix_text(bad)
            raised = False
        except _FixError:
            raised = True
        assert raised


class TestFixFile:
    def test_reformats_and_writes(self, tmp_path):
        path = tmp_path / "deck.md"
        path.write_text(DRAFT)
        result = fix_file(path, tmp_path, dry_run=False)
        assert result.changed
        assert result.card_count == 2
        assert result.uids_added == 2
        assert len(_UID_LINE.findall(path.read_text())) == 2
        # strongest net: the repaired file must validate clean (it builds)
        assert not [f for f in validate_files([path]) if f.level == "error"]

    def test_repaired_draft_validates_clean(self, tmp_path):
        # a draft with glued + malformed footnotes, repaired, must validate clean
        path = tmp_path / "deck.md"
        path.write_text(
            "---\ndeck: foo\n---\n\nq1 ::: a1\n[^uid]: short\n\n"
            "---\n\n{{c1::cloze}} card\n\n---\n\nq3 ::: a3\n\n---\n"
        )
        fix_file(path, tmp_path, dry_run=False)
        assert not [f for f in validate_files([path]) if f.level == "error"]

    def test_dry_run_does_not_write(self, tmp_path):
        path = tmp_path / "deck.md"
        path.write_text(DRAFT)
        before = path.read_text()
        result = fix_file(path, tmp_path, dry_run=True)
        assert result.changed
        assert path.read_text() == before

    def test_canonical_file_unchanged(self, tmp_path):
        path = tmp_path / "deck.md"
        path.write_text(CANONICAL)
        result = fix_file(path, tmp_path, dry_run=False)
        assert not result.changed
        assert path.read_text() == CANONICAL

    def test_symlink_skipped(self, tmp_path):
        real = tmp_path / "real.md"
        real.write_text(DRAFT)
        link = tmp_path / "link.md"
        link.symlink_to(real)
        result = fix_file(link, tmp_path, dry_run=False)
        assert result.skipped_reason == "symlink"

    def test_crlf_skipped(self, tmp_path):
        path = tmp_path / "deck.md"
        path.write_bytes(DRAFT.replace("\n", "\r\n").encode("utf-8"))
        before = path.read_bytes()
        result = fix_file(path, tmp_path, dry_run=False)
        assert result.skipped_reason == "CRLF line endings not supported"
        assert path.read_bytes() == before

    def test_unrepairable_draft_reported_not_written(self, tmp_path):
        path = tmp_path / "deck.md"
        bad = (
            "---\ndeck: foo\n---\n[^uid]: orphan0001\n\n"
            "---\n\nq1 ::: a1\n\n---\n\nq2 ::: a2\n\n---\n"
        )
        path.write_text(bad)
        result = fix_file(path, tmp_path, dry_run=False)
        assert result.error
        assert path.read_text() == bad  # untouched


class TestGitGate:
    @staticmethod
    def _git(repo, *args):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

    def test_refuses_dirty_then_stamps_clean(self, tmp_path):
        from typer.testing import CliRunner

        from app.cli.entry import app

        runner = CliRunner()
        self._git(tmp_path, "init")
        self._git(tmp_path, "config", "user.email", "t@t.t")
        self._git(tmp_path, "config", "user.name", "t")

        deck = tmp_path / "deck.md"
        deck.write_text(DECK)
        # dirty (untracked) -> refused
        result = runner.invoke(app, ["uid", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert "uncommitted changes" in result.stdout
        assert len(_UID_LINE.findall(deck.read_text())) == 1  # untouched

        # commit -> clean -> stamps
        self._git(tmp_path, "add", "deck.md")
        self._git(tmp_path, "commit", "-m", "add")
        result = runner.invoke(app, ["uid", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert len(_UID_LINE.findall(deck.read_text())) == 3
