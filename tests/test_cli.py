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
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0

        match = re.match(r"(\d+\.\d+\.\d+\n)", result.stdout)
        if not match:
            raise AssertionError(f"Unexpected version format: {result.stdout}")


class TestDecks:
    @staticmethod
    def test_deck_list():
        result = runner.invoke(
            app,
            [
                "deck",
                "list",
            ],
        )
        assert result.exit_code == 1

        result = runner.invoke(
            app,
            ["deck", "list", "--depth", "2"],
        )
        assert result.exit_code == 0
