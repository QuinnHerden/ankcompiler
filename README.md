# AnkCompiler
[![coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/QuinnHerden/882ab688aad6241baa6581d3f4adc13a/raw/ankcompiler-coverage.json)](https://github.com/QuinnHerden/ankcompiler/actions/workflows/checks.yml)

A CLI tool for compiling Anki decks, defined in Markdown.
## Installation
Run `pip install ankcompiler`
## Usage
Run `ankc --help` for usage information.

Main commands:
- `ankc build` compiles decks into `.apkg` packages.
  - Subdecks use Anki's `::` naming, e.g. `deck: Geo::Rivers`. `--deck Geo` packages `Geo` and every `Geo::...` subdeck into one `geo.apkg`. `--all` writes one package per top-level deck. Upgrading from 0.3.x: delete old per-subdeck packages (e.g. `geo--rivers.apkg`) from your output directory so they aren't re-imported.
  - New cards are studied in source order: by deck name, then file path, then position in the file. Anki applies this order to cards it imports for the first time; it doesn't reorder cards already in a collection.
  - To set the order yourself, add a `[^pos]: <n>` footnote next to a card's `[^uid]`. `<n>` is a whole number from 0 to 999999, and lower numbers are studied first. All cards from one note (both sides of a reversed note, every cloze) share its position. Within a package (the deck and subdecks one `ankc build` writes), use `[^pos]` on every card or on none. Mixing the two is an error, and so is a position used twice. A package with no `[^pos]` keeps the source order above. `ankc check` reports these errors as `file:line`. `ankc uid` and `ankc uid --fix` keep `[^pos]` lines.
- Tags: `tags:` in the frontmatter applies to every card in a file, and a `[^tag]: <tag>` footnote applies to one card. Footnote tags may use letters, digits, `_`, `-` and `::` (a hierarchical tag such as `tier::1`).
- `ankc check` validates decks without compiling. It reports problems as `file:line`, and can print JSON with `--format json`. It also fails on missing images and on two different images sharing a filename.
- `ankc uid` adds a `[^uid]` footnote to any card block that is missing one. It is append-only and safe to run more than once. Use `--check` for a dry run. It will not touch files with uncommitted git changes unless you pass `--force`.
  - Add `--fix` to also repair a draft deck whose cards are separated by a single `---`. It rewrites each card into a well-formed block and stamps any missing uids. Draft fast, then run `ankc uid --fix` to make the deck buildable. It only restructures real decks (frontmatter with a `deck:` key), so it is safe on non-drafts.
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
