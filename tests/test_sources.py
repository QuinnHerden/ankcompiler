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
