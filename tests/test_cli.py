import json
import re
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from typer.testing import CliRunner

from app.cli.entry import app

runner = CliRunner()


def _write_deck(directory, file_name, deck_name, uid, body="q ::: a"):
    (directory / file_name).write_text(
        f"---\ndeck: {deck_name}\n---\n---\n\n{body}\n\n---\n[^uid]: {uid}\n"
    )


def _package_deck_names(apkg):
    with zipfile.ZipFile(apkg) as archive, tempfile.TemporaryDirectory() as tmp:
        archive.extract("collection.anki2", tmp)
        db = sqlite3.connect(Path(tmp) / "collection.anki2")
        decks = json.loads(db.execute("select decks from col").fetchone()[0])
        db.close()
    return {deck["name"] for deck in decks.values()} - {"Default"}


class TestEntry:
    @staticmethod
    def test_default():
        result = runner.invoke(app, [])
        assert result.exit_code == 0

    @staticmethod
    def test_version():
        result = runner.invoke(
            app,
            [
                "--version",
            ],
        )
        assert result.exit_code == 0

        match = re.match(r"(\d+\.\d+\.\d+\n)", result.stdout)
        if not match:
            raise AssertionError(f"Unexpected version format: {result.stdout}")


class TestGen:
    @staticmethod
    def test_gen_chunk():
        result = runner.invoke(
            app,
            [
                "gen",
                "chunk",
            ],
        )
        assert result.exit_code == 0

    @staticmethod
    def test_gen_chunk_output_shape():
        result = runner.invoke(app, ["gen", "chunk"])
        assert result.exit_code == 0
        assert re.search(r"---\n---\n\[\^uid\]: [A-Za-z0-9]{10}\n?$", result.stdout)


class TestList:
    @staticmethod
    def test_list_deck_recurses_by_default():
        # default: search all subdirectories of --path (deck lives in tests/decks)
        result = runner.invoke(app, ["list", "deck", "--path", "tests"])
        assert result.exit_code == 0
        assert "foo" in result.stdout

    @staticmethod
    def test_list_deck_depth_limits():
        result = runner.invoke(  # root only -> deck lives deeper, so none found
            app,
            ["list", "deck", "--path", "tests", "--depth", "0"],
        )
        assert result.exit_code == 1

    @staticmethod
    def test_list_file_recurses_by_default():
        result = runner.invoke(
            app, ["list", "file", "--deck", "foo", "--path", "tests"]
        )
        assert result.exit_code == 0

    @staticmethod
    def test_list_file_depth_limits():
        result = runner.invoke(
            app,
            ["list", "file", "--deck", "foo", "--path", "tests", "--depth", "0"],
        )
        assert result.exit_code == 1


class TestCheck:
    @staticmethod
    def test_check_clean_deck():
        result = runner.invoke(app, ["check", "--deck", "foo", "--path", "tests"])
        assert result.exit_code == 0
        assert "no problems found" in result.stdout

    @staticmethod
    def test_check_invalid_selection():
        result = runner.invoke(app, ["check"])  # no --deck and no --all
        assert result.exit_code == 1
        assert "Not a valid source selection." in result.stdout


DRAFT_DECK = "---\ndeck: drafty\n---\n" "\nq1 ::: a1\n\n---\n\nq2 ::: a2\n\n---\n"


class TestUidFix:
    @staticmethod
    def test_fix_reformats_draft(tmp_path):
        deck = tmp_path / "d.md"
        deck.write_text(DRAFT_DECK)
        result = runner.invoke(
            app, ["uid", "--fix", "--force", "--path", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "reformatted" in result.stdout
        assert len(re.findall(r"\[\^uid\]: [A-Za-z0-9]{10}", deck.read_text())) == 2

    @staticmethod
    def test_fix_check_reports_without_writing(tmp_path):
        deck = tmp_path / "d.md"
        deck.write_text(DRAFT_DECK)
        before = deck.read_text()
        result = runner.invoke(
            app, ["uid", "--fix", "--check", "--force", "--path", str(tmp_path)]
        )
        assert result.exit_code == 1  # work pending
        assert "would reformat" in result.stdout
        assert deck.read_text() == before  # nothing written

    @staticmethod
    def test_fixed_draft_then_builds(tmp_path):
        deck_dir = tmp_path / "drafty"
        deck_dir.mkdir()
        (deck_dir / "d.md").write_text(DRAFT_DECK)
        out = tmp_path / "dist"
        out.mkdir()
        runner.invoke(app, ["uid", "--fix", "--force", "--path", str(tmp_path)])
        result = runner.invoke(
            app,
            [
                "build",
                "--deck",
                "drafty",
                "--path",
                str(tmp_path),
                "--depth",
                "2",
                "--output",
                str(out),
            ],
        )
        assert result.exit_code == 0
        assert list(out.glob("*.apkg"))


class TestBuild:
    @staticmethod
    def test_build_one():
        result = runner.invoke(
            app,
            [
                "build",
                "--deck",
                "foo",
                "--depth",
                "2",
            ],
        )
        assert result.exit_code == 0

    @staticmethod
    def test_build_one_recurses_by_default():
        result = runner.invoke(app, ["build", "--deck", "foo", "--path", "tests"])
        assert result.exit_code == 0

    @staticmethod
    def test_build_all():
        result = runner.invoke(
            app,
            [
                "build",
                "--all",
                "--depth",
                "2",
            ],
        )
        assert result.exit_code == 0

    @staticmethod
    def test_build_invalid_selection():
        result = runner.invoke(  # no --deck and no --all
            app,
            [
                "build",
                "--depth",
                "2",
            ],
        )
        assert result.exit_code == 1
        assert "Not a valid source selection." in result.stdout

    @staticmethod
    def test_build_aborts_on_dropped_card(tmp_path):
        # an unfixed draft would silently drop cards — build must abort
        deck_dir = tmp_path / "drafty"
        deck_dir.mkdir()
        (deck_dir / "d.md").write_text(DRAFT_DECK)
        result = runner.invoke(
            app,
            ["build", "--deck", "drafty", "--path", str(tmp_path), "--depth", "2"],
        )
        assert result.exit_code == 1
        assert "silently dropped" in result.stdout


class TestSubdecks:
    @staticmethod
    def _tree(tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        _write_deck(src, "p.md", "Geo", "aaaaaaaaa0")
        _write_deck(src, "a.md", "Geo::Rivers::Tier 1", "aaaaaaaaa1")
        _write_deck(src, "b.md", '"Geo :: Rivers :: Tier 2"', "aaaaaaaaa2")
        _write_deck(src, "c.md", "Geography", "aaaaaaaaa3")
        _write_deck(src, "d.md", "2024", "aaaaaaaaa4")
        out = tmp_path / "out"
        out.mkdir()
        return src, out

    @staticmethod
    def _build(src, out, *args):
        return runner.invoke(
            app, ["build", *args, "--path", str(src), "--output", str(out)]
        )

    @staticmethod
    def test_build_deck_bundles_parent_and_subdecks(tmp_path):
        src, out = TestSubdecks._tree(tmp_path)
        result = TestSubdecks._build(src, out, "--deck", "Geo")
        assert result.exit_code == 0
        assert [p.name for p in out.glob("*.apkg")] == ["geo.apkg"]
        assert _package_deck_names(out / "geo.apkg") == {
            "Geo",
            "Geo::Rivers::Tier 1",
            "Geo::Rivers::Tier 2",
        }

    @staticmethod
    def test_build_mid_level_subtree(tmp_path):
        src, out = TestSubdecks._tree(tmp_path)
        result = TestSubdecks._build(src, out, "--deck", "Geo::Rivers")
        assert result.exit_code == 0
        assert _package_deck_names(out / "geo--rivers.apkg") == {
            "Geo::Rivers::Tier 1",
            "Geo::Rivers::Tier 2",
        }

    @staticmethod
    def test_build_all_one_package_per_root(tmp_path):
        src, out = TestSubdecks._tree(tmp_path)
        result = TestSubdecks._build(src, out, "--all")
        assert result.exit_code == 0
        assert sorted(p.name for p in out.glob("*.apkg")) == [
            "2024.apkg",
            "geo.apkg",
            "geography.apkg",
        ]
        assert _package_deck_names(out / "geography.apkg") == {"Geography"}
        assert len(_package_deck_names(out / "geo.apkg")) == 3

    @staticmethod
    def test_build_all_aborts_on_package_name_collision(tmp_path):
        src, out = TestSubdecks._tree(tmp_path)
        _write_deck(src, "e.md", "geo::Lakes", "aaaaaaaaa5")
        result = TestSubdecks._build(src, out, "--all")
        assert result.exit_code == 1
        assert "same package file" in result.stdout
        assert not list(out.glob("*.apkg"))

    @staticmethod
    def test_build_rejects_deck_and_all_together(tmp_path):
        src, out = TestSubdecks._tree(tmp_path)
        result = TestSubdecks._build(src, out, "--all", "--deck", "Geo")
        assert result.exit_code == 1
        assert "not both" in result.stdout

    @staticmethod
    def test_check_deck_covers_subdecks(tmp_path):
        src, _ = TestSubdecks._tree(tmp_path)
        (src / "bad.md").write_text("---\ndeck: Geo::Lakes\n---\nq ::: a\n")
        result = runner.invoke(app, ["check", "--deck", "Geo", "--path", str(src)])
        assert result.exit_code == 1
        assert "bad.md" in result.stdout

    @staticmethod
    def test_check_unknown_deck_fails(tmp_path):
        src, _ = TestSubdecks._tree(tmp_path)
        result = runner.invoke(app, ["check", "--deck", "Nope", "--path", str(src)])
        assert result.exit_code == 1


class TestMediaValidation:
    @staticmethod
    def test_missing_image_fails_check_and_build(tmp_path):
        _write_deck(tmp_path, "m.md", "Maps", "bbbbbbbbb1", body="![](gone.png) ::: a")
        check = runner.invoke(app, ["check", "--deck", "Maps", "--path", str(tmp_path)])
        assert check.exit_code == 1
        assert "image not found" in check.stdout
        out = tmp_path / "out"
        out.mkdir()
        build = runner.invoke(
            app,
            ["build", "--deck", "Maps", "--path", str(tmp_path), "--output", str(out)],
        )
        assert build.exit_code == 1
        assert not list(out.glob("*.apkg"))

    @staticmethod
    def test_basename_collision_across_subdecks_fails_check(tmp_path):
        for sub in ("a", "b"):
            (tmp_path / sub).mkdir()
            (tmp_path / sub / "map.png").write_bytes(sub.encode())
        _write_deck(
            tmp_path / "a", "a.md", "Geo::A", "bbbbbbbbb2", "![](map.png) ::: a"
        )
        _write_deck(
            tmp_path / "b", "b.md", "Geo::B", "bbbbbbbbb3", "![](map.png) ::: b"
        )
        result = runner.invoke(app, ["check", "--deck", "Geo", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert "media basename collision" in result.stdout

    @staticmethod
    def test_same_basename_in_separate_packages_is_allowed(tmp_path):
        for sub, deck in (("a", "Geo"), ("b", "Hist")):
            (tmp_path / sub).mkdir()
            (tmp_path / sub / "map.png").write_bytes(sub.encode())
            _write_deck(
                tmp_path / sub,
                f"{sub}.md",
                deck,
                f"ccccccccc{sub}",
                "![](map.png) ::: a",
            )
        result = runner.invoke(app, ["check", "--all", "--path", str(tmp_path)])
        assert result.exit_code == 0

    @staticmethod
    def test_non_string_tags_do_not_crash_check(tmp_path):
        (tmp_path / "t.md").write_text(
            "---\ndeck: Tags\ntags: [1]\n---\n---\n\nq ::: a\n\n---\n[^uid]: ddddddddd1\n"
        )
        result = runner.invoke(
            app, ["check", "--deck", "Tags", "--path", str(tmp_path)]
        )
        assert result.exception is None or isinstance(result.exception, SystemExit)
