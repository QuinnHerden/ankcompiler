# AnkCompiler
[![coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/QuinnHerden/882ab688aad6241baa6581d3f4adc13a/raw/ankcompiler-coverage.json)](https://github.com/QuinnHerden/ankcompiler/actions/workflows/checks.yml)

A CLI tool for compiling Anki decks, defined in Markdown.
## Installation
Run `pip install ankcompiler`
## Usage
Run `ankc --help` for usage information.

Main commands:
- `ankc build` compiles decks into `.apkg` packages.
- `ankc check` validates decks without compiling. It reports problems as `file:line`, and can print JSON with `--format json`.
- `ankc uid` adds a `[^uid]` footnote to any card block that is missing one. It is safe to run more than once. Use `--check` for a dry run. It will not touch files with uncommitted git changes unless you pass `--force`.
  - Add `--fix` to also repair a draft deck whose cards are separated by a single `---`: it rewrites them into well-formed card blocks and stamps any missing uids. So you can draft fast, then `ankc uid --fix` to make the deck buildable.
### Examples
See [`examples/example.md`](examples/example.md) for a deck with every note type, tags, and math.
### Note types
- Question and answer: `front ::: back`. Found automatically.
- Cloze: `{{c1:: ...}}`. Found automatically.
- Basic and reversed: `front ::: back` plus `[^type]: reversed`. This makes a card in both directions.
- Type in the answer: `question ::: answer` plus `[^type]: type-in`.

Reversed and type-in cards use the same `:::` syntax as a question and answer card. So you name them with a `[^type]` footnote next to the `[^uid]`.
### Math
Write inline math as `$...$` and block math as `$$...$$`. Anki renders it with MathJax. To show a real dollar sign, write `\$`.
## Credits
Inspiration taken from [lukesmurry](https://github.com/lukesmurray/markdown-anki-decks)
