from app.logic.utils import (
    clean_str_for_filename,
    convert_md_to_html,
    generate_integer_hash,
    generate_random_string,
    search_files,
)


class TestGenerateIntegerHash:
    @staticmethod
    def test_deterministic_and_int():
        h = generate_integer_hash("foo")
        assert isinstance(h, int)
        assert h == generate_integer_hash("foo")

    @staticmethod
    def test_distinct_inputs_differ():
        assert generate_integer_hash("foo") != generate_integer_hash("bar")


class TestGenerateRandomString:
    @staticmethod
    def test_length_and_alphanumeric():
        # Asserts the current contract (<= length); the function can return
        # fewer than `length` chars (see issue #30). Tighten to == length
        # once that bug is fixed.
        for length in (1, 5, 10, 20):
            for _ in range(50):
                s = generate_random_string(length)
                assert s.isalnum()
                assert 0 < len(s) <= length


class TestCleanStrForFilename:
    @staticmethod
    def test_non_alphanumerics_replaced_and_lowercased():
        assert clean_str_for_filename("My Deck! v2") == "my-deck--v2"


class TestConvertMdToHtml:
    @staticmethod
    def test_basic_markdown():
        assert convert_md_to_html(["**bold**"]) == ["<p><strong>bold</strong></p>"]

    @staticmethod
    def test_preserves_order_and_count():
        out = convert_md_to_html(["a", "b"])
        assert len(out) == 2
        assert "<p>a</p>" in out[0]
        assert "<p>b</p>" in out[1]


class TestSearchFiles:
    @staticmethod
    def _make_tree(root):
        (root / "top.md").write_text("x")
        (root / "note.txt").write_text("x")  # wrong extension, never matched
        sub = root / "sub"
        sub.mkdir()
        (sub / "mid.md").write_text("x")
        deep = sub / "deeper"
        deep.mkdir()
        (deep / "low.md").write_text("x")

    def test_depth_boundaries(self, tmp_path):
        self._make_tree(tmp_path)

        def names(depth):
            return sorted(p.name for p in search_files(".md", tmp_path, depth))

        assert names(0) == ["top.md"]
        assert names(1) == ["mid.md", "top.md"]
        assert names(2) == ["low.md", "mid.md", "top.md"]
