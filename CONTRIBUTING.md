# Contributing

## Development setup

This project uses [uv](https://docs.astral.sh/uv/).

```sh
uv sync            # install runtime + dev dependencies into .venv
```

## Checks

CI runs the same checks on every pull request. Run them before you push:

```sh
make check         # release-version check, format, security, tests
```

You can also run each step on its own:

| Command | What it does |
|---|---|
| `make format` | `uv run black --check .` |
| `make secure` | `uv run bandit -r app -ll` |
| `make test` | `uv run pytest` |
| `make coverage` | tests with a coverage report |

Run any tool directly with `uv run <tool>` if you prefer.

## Branching

Branch off `dev` and open pull requests against `dev`, not `main`.

```sh
git switch dev
git switch -c fix/<issue>-short-description
```

Use a `fix/`, `feature/`, or `docs/` prefix. Keep the `VERSION` in `app/config.py`
and the `version` in `pyproject.toml` the same. The release check fails if they
differ, so bump both together. Use a minor bump for a behavior change and a patch
bump for a fix.

## Authoring decks

See [`examples/example.md`](examples/example.md) for a deck with every note type,
tags, and math. The README explains the format. These commands help while you edit:

```sh
ankc check --deck <name> --path <dir>   # validate without compiling
ankc uid --path <dir>                   # add a uid to any card block missing one
```
