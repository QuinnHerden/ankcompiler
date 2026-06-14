import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from genanki.deck import Deck as GenAnkiDeck
from genanki.model import Model as GenAnkiModel
from genanki.note import Note as GenAnkiNote
from genanki.package import Package as GenAnkiPackage

from app.config import settings
from app.logic.utils import (
    clean_str_for_filename,
    convert_md_to_html,
    generate_integer_hash,
    parse_markdown_file,
    search_markdown_files,
)


@dataclass
class Deck:
    name: str
    source_search_path: Path
    source_search_depth: Optional[int]

    def compile(self, output_path: Path) -> None:
        """Packages a deck."""
        deck_id = generate_integer_hash(self.name)
        deck = GenAnkiDeck(deck_id=deck_id, name=self.name)
        package = GenAnkiPackage(deck)

        chunks = self._get_chunks()
        images = []
        for chunk in chunks:
            note = chunk.extract_note()

            images.extend(note.images)

            deck.add_note(
                GenAnkiNote(
                    model=note.model, fields=note.fields, tags=note.tags, guid=note.guid
                )
            )

        package.media_files = self._dedupe_media(images)

        file_name = clean_str_for_filename(self.name)
        write_path = Path(f"{output_path}/{file_name}.apkg")
        package.write_to_file(write_path)

    @staticmethod
    def _dedupe_media(images: List[Path]) -> List[Path]:
        """De-duplicate media paths, erroring on basename collisions.

        Anki keys media by basename, so two distinct files sharing a name
        (e.g. ``a/diagram.png`` and ``b/diagram.png``) would silently clobber
        each other in the package. De-duplicate identical files (same resolved
        path) and raise on a genuine basename collision.
        """
        by_basename: dict = {}  # basename -> resolved path
        deduped: List[Path] = []

        for image in images:
            resolved = image.resolve()
            existing = by_basename.get(image.name)

            if existing is not None:
                if existing == resolved:
                    continue  # same file referenced again
                raise ValueError(
                    f"Media basename collision: '{image.name}' refers to both "
                    f"{existing} and {resolved}"
                )

            by_basename[image.name] = resolved
            deduped.append(image)

        return deduped

    def _get_chunks(self) -> List["Chunk"]:
        """Returns list of all chunks within scope."""
        source_files = self.get_source_files()

        chunks = []
        for source in source_files:
            chunks.extend(source.extract_chunks())

        return chunks

    def get_source_files(self) -> List["File"]:
        """Returns list of all source files within scope."""
        file_paths = self.get_source_file_paths()

        source_files = []
        for file_path in file_paths:
            source_file = self._extract_source_file(file_path)
            source_files.append(source_file)

        return source_files

    def get_source_file_paths(self) -> List[Path]:
        """Returns list of all source file paths."""
        markdown_files = search_markdown_files(
            search_path=self.source_search_path, search_depth=self.source_search_depth
        )

        deck_paths = []
        for file_path in markdown_files:
            meta = parse_markdown_file(file_path=file_path)[0]

            deck_name = meta.get(settings.DECK_TITLE_KEY)

            if deck_name == self.name:
                deck_paths.append(file_path)

        return deck_paths

    def _extract_source_file(self, file_path: Path) -> "File":
        """Creates source file from a markdown file."""

        meta, body = parse_markdown_file(file_path=file_path)
        file = File(path=file_path, meta=meta, body=body)

        return file


@dataclass
class File:
    path: Path
    body: str
    meta: Optional[dict]

    def extract_chunks(self) -> List["Chunk"]:
        """Splits markdown file into list of its note chunks."""

        uid_exp = (
            rf"(?:\[\^{settings.GUID_KEY}\]:"
            + r" *[A-Za-z0-9]{10}\n+)"  # [^uid]: abc1234XYZ
        )
        tag_exp = rf"(?:\[\^{settings.TAG_KEY}\]: *.+?\n+)"  # [^tag]: tag_name
        type_exp = rf"(?:\[\^{settings.TYPE_KEY}\]: *.+?\n+)"  # [^type]: reversed

        # Footnotes (uid/tag/type) may appear in any order after the block.
        meta_exp = rf"((?:{uid_exp}|{tag_exp}|{type_exp})*)"

        note_exp = r"(?:---\n\s*\n+(.(?:.|\n)+?.)\n\s*\n---\n+)"  # triple "-" delimited w/ internal newline padding
        combined_exp = rf"({note_exp}{meta_exp}?)"

        card_matches = re.findall(combined_exp, self.body)

        note_chunks = []
        for match in card_matches:
            chunk = Chunk(body=match[1], meta=match[0], file=self)
            note_chunks.append(chunk)

        return note_chunks

    def get_tags(self) -> List[str]:
        """Returns tags in frontmatter"""
        fm_tags_extract = self.meta.get(settings.META_TAG_KEY)

        if fm_tags_extract is not None and isinstance(fm_tags_extract, list):
            meta_tags = [tag.strip() for tag in fm_tags_extract]

        elif fm_tags_extract is not None and isinstance(fm_tags_extract, str):
            meta_tags = [fm_tags_extract]

        else:
            meta_tags = []

        return meta_tags

    def get_name(self) -> str:
        """Return title of the file"""
        return Path(self.path).name


@dataclass
class Chunk:
    meta: str
    body: str
    file: "File"

    def extract_note(self) -> "Note":
        """Extracts a note from a note chunk."""

        meta_dict = self._extract_meta()

        guid = meta_dict.get(settings.GUID_KEY)
        tags = meta_dict.get(settings.TAG_KEY)

        if guid is None:
            raise ValueError("No guid found in note meta chunk")

        note_type = self._resolve_type(meta_dict)
        html_fields = self._extract_html_fields(note_type)
        fields = [*html_fields, self.file.get_name()]

        meta_tags = self.file.get_tags()

        tags.extend(meta_tags)
        tags = list(dict.fromkeys(tags))

        images = self._extract_images(html_fields)

        note = Note(
            guid=guid,
            model=note_type.model,
            fields=fields,
            tags=tags,
            source=self.file,
            images=images,
        )

        return note

    def _extract_meta(self) -> dict:
        """
        Extracts footer metadata from note chunk.
        """
        meta_dict = {
            settings.GUID_KEY: None,
            settings.TAG_KEY: [],
            settings.TYPE_KEY: None,
        }

        # Value pattern is [\w-]+ (word chars + hyphen, e.g. "type-in"); keep
        # in sync with the footnote value patterns in File.extract_chunks.
        matches = re.findall(
            r"(\[\^(\w+)\]: *([\w-]+))", self.meta
        )  # [^example_key]: example-value

        pairs = []
        for match in matches:
            key = match[1]
            value = match[2]
            pairs.append((key, value))

        for key, value in pairs:
            value = value.strip()

            if key not in meta_dict:
                continue

            if isinstance(meta_dict[key], list):
                meta_dict[key].append(value)
            else:
                meta_dict[key] = value

        return meta_dict

    def _extract_type(self) -> "NoteType":
        """Resolves the note type for this chunk (parsing meta on demand)."""
        return self._resolve_type(self._extract_meta())

    def _resolve_type(self, meta_dict: dict) -> "NoteType":
        """Resolves the note type from already-parsed metadata.

        If a ``[^type]`` footnote is declared it selects the type by key;
        otherwise the type is auto-detected by matching the body against the
        auto-detectable types (QA, Cloze). Types that share the ``:::`` field
        syntax (reversed, type-in) must be declared explicitly to avoid
        ambiguous auto-detection.
        """
        types = NoteType.get_types()

        declared = meta_dict.get(settings.TYPE_KEY)
        if declared is not None:
            declared = declared.strip().lower()
            for type_ in types:
                if type_.key == declared:
                    return type_
            valid = ", ".join(t.key for t in types)
            raise ValueError(f"Unknown note type '{declared}'. Valid types: {valid}")

        matches = []
        for type_ in types:
            if not type_.auto_detect:
                continue
            match = re.compile(type_.regex, re.DOTALL).findall(self.body)
            if len(match) > 0:
                matches.append(type_)

        if len(matches) == 0:
            raise ValueError("Could not find a note type for chunk")

        if len(matches) > 1:
            raise ValueError("Found more than one note type for chunk")

        return matches[0]

    def _extract_html_fields(self, note_type: "NoteType") -> List[str]:
        """Extracts HTML fields from note chunk."""
        md_fields = self._extract_md_fields(note_type)
        html_fields = convert_md_to_html(md_fields)

        return html_fields

    def _extract_md_fields(self, note_type: "NoteType") -> List[str]:
        """Extracts markdown fields from note chunk."""
        matches = re.compile(note_type.regex, re.DOTALL).findall(self.body)

        if len(matches) != 1:
            raise ValueError(
                f"Could not extract {note_type.name} fields from chunk; "
                f"body does not match the expected syntax"
            )

        if isinstance(matches[0], tuple):  # need to unpack (['…', '…'])
            md_fields = list(matches[0])

        elif isinstance(matches, list):  # already in correct format ['…']
            md_fields = matches

        return md_fields

    def _extract_images(self, html_fields: List[str]) -> List[Path]:
        """Extracts image paths from already-rendered HTML fields."""
        # Relies on convert_md_to_html emitting double-quoted, single-line
        # <img> tags; revisit this pattern if the renderer changes.
        regex = r'<img[^>]*src="([^"]*)"'

        relative_image_paths = []
        for field in html_fields:
            relative_image_paths.extend(re.findall(regex, field))

        full_image_paths = [
            Path(self.file.path).parent / x for x in relative_image_paths
        ]
        return full_image_paths


@dataclass
class Note:
    guid: str
    model: GenAnkiModel
    fields: List[str]
    tags: List[str]
    source: File
    images: List[Path]


@dataclass
class NoteType:
    name: str
    key: str  # value used in a [^type] footnote to select this type
    regex: str
    model: GenAnkiModel
    auto_detect: bool = True  # whether the body can be matched without [^type]

    @staticmethod
    def get_types() -> List["NoteType"]:
        """Provides the master list of 'block' (note) types"""
        qa_regex = r"(.+):::(.+)"
        return [
            NoteType(
                name="QA",
                key="qa",
                regex=qa_regex,
                model=GenAnkiModel(
                    model_id="1764365620",
                    name="AnkCompiler-Question_Answer",
                    fields=[
                        {"name": "Question"},
                        {"name": "Answer"},
                        {"name": "Source"},
                    ],
                    templates=[
                        {
                            "name": "QA",
                            "qfmt": "{{Question}}",
                            "afmt": "{{Question}}" + "<hr id=answer>" + "{{Answer}}",
                        },
                    ],
                    css=f'@import url("{settings.MASTER_STYLESHEET}");',
                    model_type=GenAnkiModel.FRONT_BACK,
                ),
            ),
            NoteType(
                name="Cloze",
                key="cloze",
                regex=r"(.*(?:\{{ *c\d+ *:: *[\s\S]+? *\}})+.*)",
                model=GenAnkiModel(
                    model_id="1783507665",
                    name="AnkCompiler-Cloze",
                    fields=[{"name": "Text"}, {"name": "Source"}],
                    templates=[
                        {
                            "name": "Cloze",
                            "qfmt": "{{cloze:Text}}",
                            "afmt": "{{cloze:Text}}",
                        },
                    ],
                    css=f'@import url("{settings.MASTER_STYLESHEET}");',
                    model_type=GenAnkiModel.CLOZE,
                ),
            ),
            # Shares the QA ::: field syntax; must be declared via [^type]
            # because its body is indistinguishable from a QA card.
            NoteType(
                name="Basic-Reversed",
                key="reversed",
                regex=qa_regex,
                auto_detect=False,
                model=GenAnkiModel(
                    model_id="1764365630",
                    name="AnkCompiler-Basic-Reversed",
                    fields=[
                        {"name": "Front"},
                        {"name": "Back"},
                        {"name": "Source"},
                    ],
                    templates=[
                        {
                            "name": "Forward",
                            "qfmt": "{{Front}}",
                            "afmt": "{{Front}}<hr id=answer>{{Back}}",
                        },
                        {
                            "name": "Reverse",
                            "qfmt": "{{Back}}",
                            "afmt": "{{Back}}<hr id=answer>{{Front}}",
                        },
                    ],
                    css=f'@import url("{settings.MASTER_STYLESHEET}");',
                    model_type=GenAnkiModel.FRONT_BACK,
                ),
            ),
            NoteType(
                name="Type-In",
                key="type-in",
                regex=qa_regex,
                auto_detect=False,
                model=GenAnkiModel(
                    model_id="1764365640",
                    name="AnkCompiler-Type-In",
                    fields=[
                        {"name": "Question"},
                        {"name": "Answer"},
                        {"name": "Source"},
                    ],
                    templates=[
                        {
                            "name": "Type-In",
                            "qfmt": "{{Question}}<br>{{type:Answer}}",
                            "afmt": "{{Question}}<hr id=answer>{{Answer}}",
                        },
                    ],
                    css=f'@import url("{settings.MASTER_STYLESHEET}");',
                    model_type=GenAnkiModel.FRONT_BACK,
                ),
            ),
        ]
