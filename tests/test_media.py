from pathlib import Path

import pytest

from app.logic.sources import Deck


class TestDedupeMedia:
    @staticmethod
    def test_identical_paths_deduped():
        images = [Path("a/x.png"), Path("a/x.png"), Path("a/y.png")]
        result = Deck._dedupe_media(images)
        assert [p.name for p in result] == ["x.png", "y.png"]

    @staticmethod
    def test_basename_collision_raises():
        images = [Path("a/diagram.png"), Path("b/diagram.png")]
        with pytest.raises(ValueError, match="basename collision.*diagram.png"):
            Deck._dedupe_media(images)

    @staticmethod
    def test_distinct_names_preserved_in_order():
        images = [Path("a/one.png"), Path("a/two.png"), Path("a/three.png")]
        result = Deck._dedupe_media(images)
        assert [p.name for p in result] == ["one.png", "two.png", "three.png"]

    @staticmethod
    def test_duplicate_then_collision():
        images = [Path("a/x.png"), Path("a/x.png"), Path("b/x.png")]
        with pytest.raises(ValueError, match="basename collision"):
            Deck._dedupe_media(images)

    @staticmethod
    def test_distinct_basenames_same_file_both_kept(tmp_path):
        """Two different names pointing at the same file (symlink) are both
        kept — genanki stores media by basename, so each name is needed."""
        real = tmp_path / "real.png"
        real.write_bytes(b"img")
        link = tmp_path / "alias.png"
        link.symlink_to(real)
        result = Deck._dedupe_media([real, link])
        assert sorted(p.name for p in result) == ["alias.png", "real.png"]

    @staticmethod
    def test_empty():
        assert Deck._dedupe_media([]) == []
