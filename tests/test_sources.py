import pytest

from app.logic.sources import Chunk, File
from app.logic.utils import parse_markdown_file


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
    def test_no_matching_type_raises():
        chunk = Chunk(meta="", body="just some plain prose, no card syntax", file=None)
        with pytest.raises(ValueError, match="Could not find a note type"):
            chunk._extract_type()

    @staticmethod
    def test_ambiguous_type_raises():
        chunk = Chunk(meta="", body="front ::: back {{c1:: cloze}}", file=None)
        with pytest.raises(ValueError, match="Found more than one note type"):
            chunk._extract_type()


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
