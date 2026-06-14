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
