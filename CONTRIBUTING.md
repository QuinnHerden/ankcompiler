# Contributing

## Development setup

This project uses [PDM](https://pdm-project.org/).

```sh
pdm install        # install runtime + dev dependencies
```

## Checks

CI runs the same checks on every pull request. Run them locally before pushing:

```sh
pdm run check      # release-version check + format + security + tests
```

Individual steps:

| Command | What it does |
|---|---|
| `pdm run format` | `black --check .` |
| `pdm run secure` | `bandit -r app -ll` |
| `pdm run test` | `pytest` |
| `pdm run coverage` | tests with coverage report |

## Branching

Branch off `dev` and open pull requests against `dev` (not `main`):

```sh
git switch dev
git switch -c fix/<issue>-short-description
```

Use `fix/`, `feature/`, or `docs/` prefixes. Keep `app/config.py` `VERSION`
and `pyproject.toml` `version` in sync — the release check enforces it; bump
them together (minor for behavior changes, patch for fixes).

## Authoring decks

See [`examples/example.md`](examples/example.md) for a deck exercising every
note type, tags, and math, and the README for the format. Useful while editing:

```sh
ankc check --deck <name> --path <dir>   # validate without compiling
ankc uid --path <dir>                   # stamp any card blocks missing a uid
```
