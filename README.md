# AnkCompiler
[![coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/QuinnHerden/882ab688aad6241baa6581d3f4adc13a/raw/ankcompiler-coverage.json)](https://github.com/QuinnHerden/ankcompiler/actions/workflows/checks.yml)

A CLI tool for compiling Anki decks, defined in Markdown.
## Installation
Run `pip install ankcompiler`
## Usage
Run `ankc --help` for usage information.
### Examples
An example source deck can be found in the [test deck](https://github.com/QuinnHerden/ankcompiler/blob/main/tests/decks/sample.md)
### Note types
- **Question/Answer** — `front ::: back` (detected automatically).
- **Cloze** — `{{c1:: ...}}` (detected automatically).
- **Basic-and-reversed** — `front ::: back` with `[^type]: reversed`; generates both directions.
- **Type-in-answer** — `question ::: answer` with `[^type]: type-in`.

Reversed and type-in cards share the `:::` syntax, so declare them explicitly with a `[^type]` footnote alongside `[^uid]`.
### Math
Inline (`$...$`) and block (`$$...$$`) LaTeX is rendered by Anki's MathJax. Use `\$` for a literal dollar sign.
## Credits
Inspiration taken from [lukesmurry](https://github.com/lukesmurray/markdown-anki-decks)
