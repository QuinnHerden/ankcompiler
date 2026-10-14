from pathlib import Path

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

    def test_merged_cards_is_error_not_warning(self, tmp_path):
        # two cards sharing a single "---": the second has no opening delimiter
        # and would be silently dropped at compile time. Must be an error so the
        # build aborts rather than losing the card.
        path = write_deck(
            tmp_path,
            "---\ndeck: foo\n---\n" "---\n\nq1 ::: a1\n\n---\n\nq2 ::: a2\n\n---\n",
        )
        findings = validate_files([path])
        merged = [f for f in findings if "silently dropped" in f.message]
        assert len(merged) == 1
        assert merged[0].level == "error"

    def test_prose_outside_block_not_flagged(self, tmp_path):
        # explanatory prose before the first card block is intentionally
        # ignored (see examples/example.md), not a dropped card
        path = write_deck(
            tmp_path,
            "---\ndeck: foo\n---\n"
            "This paragraph documents the deck and is ignored.\n\n"
            "---\n\nq ::: a\n\n---\n[^uid]: abc1234567\n",
        )
        findings = validate_files([path])
        assert not any("silently dropped" in f.message for f in findings)

    def test_dropped_cloze_card_flagged(self, tmp_path):
        # a cloze card sharing a single "---" with its neighbor would be dropped
        path = write_deck(
            tmp_path,
            "---\ndeck: foo\n---\n"
            "---\n\nq1 ::: a1\n\n---\n[^uid]: abc1234567\n\n"
            "{{c1::orphaned}} cloze\n\n---\n",
        )
        findings = validate_files([path])
        dropped = [f for f in findings if "silently dropped" in f.message]
        assert len(dropped) == 1
        assert dropped[0].level == "error"

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


POSITIONS = Path(__file__).parent / "decks" / "positions"


def _fixture_files(name):
    return sorted((POSITIONS / name).glob("*.md"))


class TestPositions:
    def test_valid_positions_have_no_findings(self):
        assert validate_files(_fixture_files("valid")) == []

    def test_no_positions_has_no_findings(self):
        assert validate_files(_fixture_files("unpositioned")) == []

    def test_mixed_names_files_at_first_unpositioned_card(self):
        findings = validate_files(_fixture_files("mixed"))
        assert len(findings) == 1
        finding = findings[0]
        assert finding.file.name == "b.md" and finding.line == 4
        assert "mixes cards with and without [^pos]" in finding.message
        assert "mixed/a.md" in finding.message and "mixed/b.md" in finding.message

    def test_duplicate_names_both_cards(self):
        findings = validate_files(_fixture_files("duplicate"))
        assert len(findings) == 1
        finding = findings[0]
        assert finding.format().startswith(f"{POSITIONS}/duplicate/b.md:4: error:")
        assert "duplicate [^pos] 5" in finding.message
        assert f"dupe000001 at {POSITIONS}/duplicate/a.md:4" in finding.message
        assert f"dupe000002 at {POSITIONS}/duplicate/b.md:4" in finding.message

    def test_invalid_values_reported_at_card_line(self):
        findings = validate_files(_fixture_files("invalid"))
        assert [(f.line, f.message) for f in findings] == [
            (4, "invalid [^pos] '1000000': must be a whole number from 0 to 999999"),
            (12, "invalid [^pos] '-1': must be a whole number from 0 to 999999"),
            (20, "invalid [^pos] '1.5': must be a whole number from 0 to 999999"),
        ]

    def test_rules_apply_per_top_level_deck(self, tmp_path):
        positioned = write_deck(
            tmp_path,
            "---\ndeck: one\n---\n---\n\nq ::: a\n\n---\n"
            "[^uid]: abc1234567\n[^pos]: 0\n",
            name="one.md",
        )
        unpositioned = write_deck(
            tmp_path,
            "---\ndeck: two\n---\n---\n\nq ::: a\n\n---\n[^uid]: abc1234568\n",
            name="two.md",
        )
        same_pos = write_deck(
            tmp_path,
            "---\ndeck: two::sub\n---\n---\n\nq ::: b\n\n---\n"
            "[^uid]: abc1234569\n[^pos]: 0\n",
            name="sub.md",
        )
        assert validate_files([positioned, unpositioned]) == []
        mixed = validate_files([positioned, unpositioned, same_pos])
        assert [f.file for f in mixed] == [unpositioned]

    def test_empty_position_reported(self, tmp_path):
        path = write_deck(
            tmp_path,
            "---\ndeck: foo\n---\n---\n\nq ::: a\n\n---\n[^pos]:\n[^uid]: abc1234567\n",
        )
        findings = validate_files([path])
        assert [(f.line, f.message) for f in findings] == [
            (4, "invalid [^pos] '': must be a whole number from 0 to 999999")
        ]
