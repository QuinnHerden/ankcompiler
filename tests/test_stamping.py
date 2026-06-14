import re
import subprocess

from app.logic.stamping import stamp_file, stamp_text

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
