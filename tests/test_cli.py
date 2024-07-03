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


class TestList:
    @staticmethod
    def test_list_deck():
        result = runner.invoke(  # not a deep enough search
            app,
            [
                "list",
                "deck",
            ],
        )
        assert result.exit_code == 1

        result = runner.invoke(
            app,
            [
                "list",
                "deck",
                "--depth",
                "2",
            ],
        )
        assert result.exit_code == 0

    @staticmethod
    def test_list_file():
        result = runner.invoke(  # not a deep enough search
            app,
            [
                "list",
                "file",
                "--deck",
                "foo",
            ],
        )
        assert result.exit_code == 1

        result = runner.invoke(
            app,
            [
                "list",
                "file",
                "--deck",
                "foo",
                "--depth",
                "2",
            ],
        )


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
