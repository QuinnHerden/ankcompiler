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
        for length in (1, 5, 10, 20):
            for _ in range(200):
                s = generate_random_string(length)
                assert s.isalnum()
                assert len(s) == length


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

    @staticmethod
    def test_inline_math():
        (out,) = convert_md_to_html([r"$E = mc^2$"])
        assert r"\(E = mc^2\)" in out  # Anki-native MathJax delimiters

    @staticmethod
    def test_block_math():
        (out,) = convert_md_to_html([r"$$A = \pi r^2$$"])
        assert r"\[A = \pi r^2\]" in out

    @staticmethod
    def test_currency_not_treated_as_math():
        (out,) = convert_md_to_html([r"it costs $5 and $10"])
        assert "$5 and $10" in out
        assert "arithmatex" not in out

    @staticmethod
    def test_inequality_escaped_inside_math():
        # '<' is HTML-escaped even inside math; Anki's MathJax decodes it.
        (out,) = convert_md_to_html([r"$x < y$"])
        assert r"\(x &lt; y\)" in out

    @staticmethod
    def test_math_inside_table():
        out = convert_md_to_html(["| f | val |\n|---|---|\n| $x^2$ | y |"])[0]
        assert "<table>" in out
        assert r"\(x^2\)" in out


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

    def test_unlimited_depth_by_default(self, tmp_path):
        self._make_tree(tmp_path)
        found = sorted(p.name for p in search_files(".md", tmp_path))
        assert found == ["low.md", "mid.md", "top.md"]

    def test_hidden_directories_skipped(self, tmp_path):
        self._make_tree(tmp_path)
        hidden = tmp_path / ".git"
        hidden.mkdir()
        (hidden / "internal.md").write_text("x")
        found = sorted(p.name for p in search_files(".md", tmp_path))
        assert "internal.md" not in found

    def test_symlink_cycle_does_not_recurse(self, tmp_path):
        self._make_tree(tmp_path)
        loop = tmp_path / "sub" / "loop"
        loop.symlink_to(tmp_path, target_is_directory=True)  # points back to root
        # must terminate (no infinite recursion) and ignore the symlinked dir
        found = sorted(p.name for p in search_files(".md", tmp_path))
        assert found == ["low.md", "mid.md", "top.md"]
