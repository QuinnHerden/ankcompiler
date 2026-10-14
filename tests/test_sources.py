import sqlite3
import tempfile
import zipfile
from pathlib import Path

import pytest

from app.logic.sources import (
    Chunk,
    Deck,
    File,
    Placement,
    compile_package,
    position_problems,
)
from app.logic.utils import clean_str_for_filename, parse_markdown_file


def build_note(tmp_path, body, frontmatter="deck: foo", meta="[^uid]: abc1234567"):
    """Compile a single-card deck and return its extracted Note."""
    deck = tmp_path / "deck.md"
    deck.write_text(f"---\n{frontmatter}\n---\n---\n\n{body}\n\n---\n{meta}\n")
    parsed_meta, parsed_body = parse_markdown_file(deck)
    chunks = File(path=deck, meta=parsed_meta, body=parsed_body).extract_chunks()
    assert len(chunks) == 1
    return chunks[0].extract_note()


class TestDeclaredNoteType:
    def test_reversed_uses_two_templates(self, tmp_path):
        note = build_note(
            tmp_path,
            "front ::: back",
            meta="[^uid]: abc1234567\n[^type]: reversed",
        )
        assert note.model.name == "AnkCompiler-Basic-Reversed"
        assert len(note.model.templates) == 2
        assert note.fields[:2] == note.fields[:2]  # front/back rendered
        assert "front" in note.fields[0]
        assert "back" in note.fields[1]

    def test_type_in_uses_type_template(self, tmp_path):
        note = build_note(
            tmp_path,
            "capital of France ::: Paris",
            meta="[^uid]: abc1234567\n[^type]: type-in",
        )
        assert note.model.name == "AnkCompiler-Type-In"
        assert "{{type:Answer}}" in note.model.templates[0]["qfmt"]

    def test_explicit_qa_type(self, tmp_path):
        note = build_note(tmp_path, "q ::: a", meta="[^uid]: abc1234567\n[^type]: qa")
        assert note.model.name == "AnkCompiler-Question_Answer"

    def test_unknown_type_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Unknown note type 'bogus'"):
            build_note(tmp_path, "q ::: a", meta="[^uid]: abc1234567\n[^type]: bogus")

    def test_declared_type_body_mismatch_names_type(self, tmp_path):
        # [^type]: cloze but a ::: body -> error should name the note type.
        with pytest.raises(ValueError, match="Cloze"):
            build_note(
                tmp_path, "front ::: back", meta="[^uid]: abc1234567\n[^type]: cloze"
            )

    def test_reversed_not_auto_detected_without_declaration(self, tmp_path):
        # A plain ::: card with no [^type] is QA, never ambiguous with reversed.
        note = build_note(tmp_path, "q ::: a")
        assert note.model.name == "AnkCompiler-Question_Answer"


class TestExtractType:
    @staticmethod
    def test_no_matching_type_reported():
        chunk = Chunk(
            meta="[^uid]: abc1234567", body="plain prose, no card syntax", file=None
        )
        assert any("Could not find a note type" in e for e in chunk.validate())

    @staticmethod
    def test_ambiguous_type_reported():
        chunk = Chunk(
            meta="[^uid]: abc1234567", body="front ::: back {{c1:: cloze}}", file=None
        )
        assert any("Found more than one note type" in e for e in chunk.validate())


class TestChunkValidate:
    @staticmethod
    def test_valid_chunk_has_no_errors_and_exposes_uid():
        chunk = Chunk(meta="[^uid]: abc1234567", body="q ::: a", file=None)
        assert chunk.validate() == []
        assert chunk.uid == "abc1234567"

    @staticmethod
    def test_missing_uid_reported_and_uid_none():
        chunk = Chunk(meta="", body="q ::: a", file=None)
        errors = chunk.validate()
        assert any("missing uid" in e for e in errors)
        assert chunk.uid is None

    @staticmethod
    def test_unknown_type_reported():
        chunk = Chunk(
            meta="[^uid]: abc1234567\n[^type]: bogus", body="q ::: a", file=None
        )
        assert any("Unknown note type 'bogus'" in e for e in chunk.validate())


class TestExtractMeta:
    @staticmethod
    def test_guid_and_multiple_tags():
        chunk = Chunk(
            meta="[^uid]: abc1234567\n[^tag]: t1\n[^tag]: t2\n", body="", file=None
        )
        meta = chunk._extract_meta()
        assert meta["uid"] == "abc1234567"
        assert meta["tag"] == ["t1", "t2"]

    @staticmethod
    def test_hierarchical_tag_kept_whole():
        chunk = Chunk(meta="[^uid]: abc1234567\n[^tag]: tier::1\n", body="", file=None)
        assert chunk._extract_meta()["tag"] == ["tier::1"]

    @staticmethod
    def test_missing_guid_yields_none():
        chunk = Chunk(meta="[^tag]: t1\n", body="", file=None)
        meta = chunk._extract_meta()
        assert meta["uid"] is None


class TestExtractNote:
    def test_qa_fields_and_model(self, tmp_path):
        note = build_note(tmp_path, "what is 2+2? ::: 4")
        assert "Question_Answer" in note.model.name
        assert "<p>what is 2+2?" in note.fields[0]
        assert "<p>4</p>" in note.fields[1]
        assert note.fields[-1] == "deck.md"  # source filename

    def test_qa_multiline_body(self, tmp_path):
        note = build_note(tmp_path, "question and\n:::\nanswer on\nmultiple lines")
        assert "Question_Answer" in note.model.name
        assert "question and" in note.fields[0]
        assert "multiple lines" in note.fields[1]

    def test_cloze_fields_and_model(self, tmp_path):
        note = build_note(tmp_path, "the capital is {{c1:: Paris}}")
        assert note.model.name.endswith("Cloze")
        assert "{{c1:: Paris}}" in note.fields[0]

    def test_tags_merge_frontmatter_and_note(self, tmp_path):
        note = build_note(
            tmp_path,
            "q ::: a",
            frontmatter="deck: foo\ntags:\n  - shared\n  - dup",
            meta="[^uid]: abc1234567\n[^tag]: dup\n[^tag]: own",
        )
        # note-level tags first, frontmatter tags appended, duplicates removed
        assert note.tags == ["dup", "own", "shared"]

    def test_scalar_frontmatter_tag(self, tmp_path):
        """A single scalar `tags:` value is supported, not just a list."""
        note = build_note(tmp_path, "q ::: a", frontmatter="deck: foo\ntags: solo")
        assert note.tags == ["solo"]

    @staticmethod
    def test_missing_guid_raises():
        chunk = Chunk(meta="", body="q ::: a", file=None)
        with pytest.raises(ValueError, match="No guid found"):
            chunk.extract_note()


class TestEndOfDocument:
    @staticmethod
    def test_card_block_at_eof_without_trailing_newline(tmp_path):
        """A document that ends on a card block with no trailing newline
        should still yield a parseable note with its guid intact (issue #25)."""
        deck = tmp_path / "deck.md"
        deck.write_text(
            "---\ndeck: foo\n---\n"
            "---\n\nWhat is 2+2? ::: 4\n\n---\n[^uid]: abc1234567"
        )

        meta, body = parse_markdown_file(deck)
        assert body.endswith("\n")  # normalized at the source boundary

        file = File(path=deck, meta=meta, body=body)
        chunks = file.extract_chunks()

        assert len(chunks) == 1
        assert chunks[0].extract_note().guid == "abc1234567"


class TestExtractImages:
    @staticmethod
    def _note_with_body(tmp_path, body):
        deck = tmp_path / "deck.md"
        deck.write_text(
            f"---\ndeck: foo\n---\n---\n\n{body}\n\n---\n[^uid]: abc1234567\n"
        )
        meta, parsed = parse_markdown_file(deck)
        chunks = File(path=deck, meta=meta, body=parsed).extract_chunks()
        assert len(chunks) == 1
        return chunks[0].extract_note()

    def test_images_across_multiple_fields(self, tmp_path):
        """Images in both the question and answer are all collected (#27)."""
        note = self._note_with_body(tmp_path, "what? ![q](one.png) ::: ![a](two.png)")
        names = [p.name for p in note.images]
        assert names == ["one.png", "two.png"]

    def test_multiple_images_in_one_field(self, tmp_path):
        """Two images in a single field are both collected (#27)."""
        note = self._note_with_body(tmp_path, "q ::: ![a](one.png) and ![b](two.png)")
        names = [p.name for p in note.images]
        assert names == ["one.png", "two.png"]


POSITIONS = Path(__file__).parent / "decks" / "positions"


def _compile(tmp_path, fixture, *deck_names):
    decks = [
        Deck(
            name=name, source_search_path=POSITIONS / fixture, source_search_depth=None
        )
        for name in deck_names
    ]
    compile_package(name=deck_names[0], decks=decks, output_path=tmp_path)
    return tmp_path / f"{clean_str_for_filename(deck_names[0])}.apkg"


def _cards(apkg):
    """(due, guid, card ord) for every card, ordered by due then ord."""
    with zipfile.ZipFile(apkg) as archive, tempfile.TemporaryDirectory() as tmp:
        archive.extract("collection.anki2", tmp)
        db = sqlite3.connect(Path(tmp) / "collection.anki2")
        rows = db.execute(
            "select c.due, n.guid, c.ord from cards c join notes n on n.id = c.nid"
            " order by c.due, c.ord"
        ).fetchall()
        db.close()
    return rows


class TestChunkPosition:
    @staticmethod
    @pytest.mark.parametrize(
        "meta, expected",
        [
            ("[^uid]: abc1234567\n", None),
            ("[^uid]: abc1234567\n[^pos]: 0\n", 0),
            ("[^pos]: 42\n[^uid]: abc1234567\n", 42),
            ("[^uid]: abc1234567\n[^pos]: 999999  \n", 999999),
            ("[^uid]: abc1234567\n[^pos]: 007\n", 7),
        ],
    )
    def test_valid(meta, expected):
        chunk = Chunk(meta=meta, body="q ::: a", file=None)
        assert chunk.position == expected
        assert chunk.has_position == (expected is not None)
        assert chunk.validate() == []

    @staticmethod
    @pytest.mark.parametrize(
        "value", ["1000000", "-1", "+1", "1.5", "1e3", "x", "1_0", ""]
    )
    def test_invalid_value(value):
        chunk = Chunk(
            meta=f"[^uid]: abc1234567\n[^pos]: {value}\n", body="q ::: a", file=None
        )
        assert chunk.has_position
        with pytest.raises(ValueError, match="invalid \\[\\^pos\\]"):
            chunk.position
        assert any("invalid [^pos]" in e for e in chunk.validate())

    @staticmethod
    def test_repeated_footnote():
        chunk = Chunk(
            meta="[^uid]: abc1234567\n[^pos]: 1\n[^pos]: 2\n", body="q ::: a", file=None
        )
        assert any("more than one [^pos]" in e for e in chunk.validate())

    def test_pos_before_uid_keeps_uid(self, tmp_path):
        note = build_note(tmp_path, "q ::: a", meta="[^pos]: 3\n[^uid]: abc1234567")
        assert note.guid == "abc1234567"
        assert note.position == 3


class TestCompilePositions:
    @staticmethod
    def test_positions_become_due(tmp_path):
        apkg = _compile(tmp_path, "valid", "Positions", "Positions::Sub")
        assert _cards(apkg) == [
            (0, "posvalid02", 0),
            (10, "posvalid03", 0),
            (10, "posvalid03", 1),  # both cards of a reversed note share its due
            (20, "posvalid01", 0),
        ]

    @staticmethod
    def test_without_positions_numbers_in_source_order(tmp_path):
        # Regression: a package with no [^pos] builds exactly as in 0.5.
        apkg = _compile(tmp_path, "unpositioned", "Unpositioned", "Unpositioned::Sub")
        assert _cards(apkg) == [
            (0, "unpos00001", 0),
            (1, "unpos00002", 0),
            (1, "unpos00002", 1),
            (2, "unpos00003", 0),
        ]

    @staticmethod
    def test_mixed_package_names_files(tmp_path):
        with pytest.raises(ValueError) as exc:
            _compile(tmp_path, "mixed", "Mixed")
        message = str(exc.value)
        assert "mixes cards with and without [^pos]" in message
        assert "Missing in: " in message and "mixed/b.md" in message
        assert "Present in: " in message and "mixed/a.md" in message
        assert not list(tmp_path.glob("*.apkg"))

    @staticmethod
    def test_duplicate_position_names_both_cards(tmp_path):
        with pytest.raises(ValueError, match="duplicate \\[\\^pos\\] 5") as exc:
            _compile(tmp_path, "duplicate", "Duplicate")
        assert "dupe000001" in str(exc.value)
        assert "dupe000002" in str(exc.value)

    @staticmethod
    def test_invalid_position_aborts(tmp_path):
        with pytest.raises(ValueError, match="invalid \\[\\^pos\\] '1000000'"):
            _compile(tmp_path, "invalid", "Invalid")

    @staticmethod
    def test_positions_are_per_package(tmp_path):
        # Each package is checked on its own: an unpositioned package beside a
        # positioned one is not a mix.
        _compile(tmp_path, "valid", "Positions", "Positions::Sub")
        _compile(tmp_path, "unpositioned", "Unpositioned")


class TestPositionProblems:
    @staticmethod
    def test_no_positions_no_problems():
        placements = [
            Placement(uid="a", declared=False, position=None, path=Path("a.md"))
        ]
        assert position_problems(placements) == []

    @staticmethod
    def test_malformed_counts_as_declared_but_not_duplicate():
        placements = [
            Placement(uid="a", declared=True, position=None, path=Path("a.md")),
            Placement(uid="b", declared=True, position=None, path=Path("b.md")),
        ]
        assert position_problems(placements) == []


class TestFootnoteScope:
    def test_pos_line_in_body_is_not_a_footnote(self, tmp_path):
        note = build_note(tmp_path, "q :::\n[^pos]: 7\nanswer")
        assert note.position is None

    def test_tab_before_value(self, tmp_path):
        note = build_note(tmp_path, "q ::: a", meta="[^uid]: abc1234567\n[^pos]:\t4")
        assert note.position == 4
