from app.logic.sources import File
from app.logic.utils import parse_markdown_file


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
