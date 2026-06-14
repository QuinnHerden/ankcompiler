from app.logic.validation import (
    findings_to_dicts,
    format_findings,
    validate_files,
)


def write_deck(tmp_path, body, name="d.md"):
    path = tmp_path / name
    path.write_text(body)
    return path


class TestValidateFiles:
    def test_clean_deck_has_no_findings(self, tmp_path):
        path = write_deck(
            tmp_path,
            "---\ndeck: foo\n---\n---\n\nq ::: a\n\n---\n[^uid]: abc1234567\n",
        )
        assert validate_files([path]) == []

    def test_missing_uid(self, tmp_path):
        path = write_deck(tmp_path, "---\ndeck: foo\n---\n---\n\nq ::: a\n\n---\n")
        findings = validate_files([path])
        assert any("missing uid" in f.message for f in findings)

    def test_missing_deck_frontmatter(self, tmp_path):
        path = write_deck(tmp_path, "---\ntags:\n  - t\n---\n")
        findings = validate_files([path])
        assert any(
            "missing a 'deck' key" in f.message and f.line == 1 for f in findings
        )

    def test_duplicate_uid_cites_first_location(self, tmp_path):
        body = (
            "---\ndeck: foo\n---\n"
            "---\n\nq1 ::: a1\n\n---\n[^uid]: abc1234567\n\n"
            "---\n\nq2 ::: a2\n\n---\n[^uid]: abc1234567\n"
        )
        path = write_deck(tmp_path, body)
        findings = validate_files([path])
        dupes = [f for f in findings if "duplicate uid" in f.message]
        assert len(dupes) == 1
        assert "first seen at" in dupes[0].message

    def test_duplicate_uid_across_files(self, tmp_path):
        a = write_deck(
            tmp_path,
            "---\ndeck: foo\n---\n---\n\nq ::: a\n\n---\n[^uid]: abc1234567\n",
            name="a.md",
        )
        b = write_deck(
            tmp_path,
            "---\ndeck: foo\n---\n---\n\nq ::: b\n\n---\n[^uid]: abc1234567\n",
            name="b.md",
        )
        findings = validate_files([a, b])
        assert any("duplicate uid" in f.message for f in findings)

    def test_unknown_declared_type(self, tmp_path):
        path = write_deck(
            tmp_path,
            "---\ndeck: foo\n---\n---\n\nq ::: a\n\n---\n"
            "[^uid]: abc1234567\n[^type]: bogus\n",
        )
        findings = validate_files([path])
        assert any("Unknown note type 'bogus'" in f.message for f in findings)

    def test_malformed_unterminated_block(self, tmp_path):
        # opener with no closing delimiter
        path = write_deck(tmp_path, "---\ndeck: foo\n---\n---\n\nq ::: a\n")
        findings = validate_files([path])
        assert any("malformed or unterminated" in f.message for f in findings)

    def test_finding_reports_line_number(self, tmp_path):
        path = write_deck(tmp_path, "---\ndeck: foo\n---\n---\n\nq ::: a\n\n---\n")
        findings = validate_files([path])
        missing = next(f for f in findings if "missing uid" in f.message)
        assert missing.line == 4  # the card block's opening delimiter


class TestFormatting:
    def test_format_no_findings(self):
        assert format_findings([]) == "no problems found"

    def test_format_and_json(self, tmp_path):
        path = write_deck(tmp_path, "---\ndeck: foo\n---\n---\n\nq ::: a\n\n---\n")
        findings = validate_files([path])
        text = format_findings(findings)
        assert "error:" in text
        assert "error(s)" in text  # summary footer
        dicts = findings_to_dicts(findings)
        assert dicts[0]["level"] == "error"
        assert dicts[0]["file"] == str(path)
