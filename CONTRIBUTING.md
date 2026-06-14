# Contributing

## Development setup

This project uses [PDM](https://pdm-project.org/).

```sh
pdm install        # install runtime + dev dependencies
```

## Checks

CI runs the same checks on every pull request. Run them before you push:

```sh
pdm run check      # release-version check, format, security, tests
```

You can also run each step on its own:

| Command | What it does |
|---|---|
| `pdm run format` | `black --check .` |
| `pdm run secure` | `bandit -r app -ll` |
| `pdm run test` | `pytest` |
| `pdm run coverage` | tests with a coverage report |

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
