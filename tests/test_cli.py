import re

from typer.testing import CliRunner

from app.cli.entry import app

runner = CliRunner()


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
