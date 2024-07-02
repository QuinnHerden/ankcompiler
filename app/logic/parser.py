import logging
import re
from pathlib import Path
from typing import List, Tuple

import frontmatter
from genanki.model import Model
from genanki.note import Note
from markdown import markdown
from yaml.constructor import ConstructorError

from app.config import settings
from app.logic.notes import NoteType, get_model_cz, get_model_qa
from app.logic.utils import read_file


def split_markdown_file(file: Path) -> Tuple[dict, str]:
    """Splits markdown input string into (frontmatter, contents)."""
    try:
        split = frontmatter.parse(read_file(file))
    except ConstructorError:
        logging.warning("Could not parse file: %s", file)
        split = ({}, "")

    return split


def split_markdown_page(contents: str) -> list[Tuple[str, str]]:
    """Splits markdown input string into list of note (metadata, body)."""

    uid_exp = get_uid_expression()
    tag_exp = get_tag_expression()

    meta_exp = rf"({tag_exp}*{uid_exp}?{tag_exp}*)"

    note_exp = r"(?:---\n\s*\n+(.(?:.|\n)+?.)\n\s*\n---\n+)"  # triple "-" delimited w/ internal newline padding
    combined_exp = rf"({note_exp}{meta_exp}?)"

    card_matches = re.findall(combined_exp, contents)

    note_blocks = []
    for match in card_matches:
        note_meta = match[2].strip()
        note_body = match[1].strip()
        note_blocks.append((note_meta, note_body))

    return note_blocks


def get_uid_expression() -> str:
    """Returns expression to extract the guid from a note."""
    uid_exp = (
        rf"(?:\[\^{settings.GUID_KEY}\]:"
        + r" *[A-Za-z0-9]{10}\n+)"  # [^uid]: abc1234XYZ
    )

    return uid_exp


def get_tag_expression() -> str:
    """Returns expression to extract the tags from a note."""
    tag_exp = rf"(?:\[\^{settings.TAG_KEY}\]: *.+?\n+)"  # [^tag]: tag_name

    return tag_exp


def parse_note_block(block: Tuple[str, str]) -> Note:
    """Parses a single note block."""

    def parse_note_meta(meta: str) -> tuple[str, List[str]]:
        meta_dict = extract_meta(contents=meta)
        guid = meta_dict.get(settings.GUID_KEY)
        tags = meta_dict.get(settings.TAG_KEY)
        if guid is None:
            raise ValueError("No guid found in note meta block")

        return guid, tags

    def parse_note_body(body: str) -> Tuple[Model, List[str]]:
        note_type = classify_note(contents=body)

        model = get_model(note_type=note_type)
        fields = extract_fields(contents=body, note_type=note_type)

        return model, fields

    note_meta, note_body = block[0], block[1]

    guid, tags = parse_note_meta(meta=note_meta)
    model, fields = parse_note_body(body=note_body)

    return Note(guid=guid, model=model, fields=fields, tags=tags)


def extract_meta(contents: str) -> dict:
    """
    Extracts metadata dictionary from note block contents.
    """
    meta_dict = {settings.GUID_KEY: None, settings.TAG_KEY: []}

    matches = re.findall(r"(\[\^(\w+)\]: *(.+))", contents)

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


def classify_note(contents: str) -> NoteType:
    """Classifies note type based on note block contents."""
    kind = None

    qa_regex = get_note_regex(NoteType.QUESTION_ANSWER)
    qa_match = re.compile(qa_regex, re.DOTALL).findall(contents)

    cz_regex = get_note_regex(NoteType.CLOZE)
    cz_match = re.compile(cz_regex, re.DOTALL).findall(contents)

    # ordering from most specific to least
    if cz_match:
        kind = NoteType.CLOZE

    elif qa_match:
        kind = NoteType.QUESTION_ANSWER

    if kind is None:
        raise ValueError("Invalid note type")

    return kind


def get_note_regex(note_type: NoteType) -> str:
    """
    Retrieves the regular expressions used for the passed Anki note type.
    """
    regex = None

    if note_type == NoteType.QUESTION_ANSWER:
        regex = r"(.+):::(.+)"

    elif note_type == NoteType.CLOZE:
        regex = r"\{{ *c\d+ *:: *[\s\S]+? *\}}"

    if regex is None:
        raise ValueError("Invalid note type")

    return regex


def get_model(note_type: NoteType) -> Model:
    """Returns model for given note type."""
    model = None

    if note_type == NoteType.QUESTION_ANSWER:
        model = get_model_qa()

    elif note_type == NoteType.CLOZE:
        model = get_model_cz()

    if model is None:
        raise ValueError("Could not find model for note")

    return model


def extract_fields(contents: str, note_type: NoteType) -> List[str]:
    """
    Extracts fields from note block contents.
    """
    extract = None

    if note_type == NoteType.QUESTION_ANSWER:
        extract = extract_fields_qa(contents)

    elif note_type == NoteType.CLOZE:
        extract = extract_fields_cz(contents)

    if extract is None:
        raise ValueError("Could not extract contents from note")

    return extract


def extract_fields_qa(contents: str) -> List[str]:
    """
    Extracts question and answer fields from note block contents.
    """
    qa_regex = get_note_regex(NoteType.QUESTION_ANSWER)
    matches = re.compile(qa_regex, re.DOTALL).findall(contents)
    if len(matches) != 1:
        raise ValueError("Could not extract fields from note")

    md_fields = matches[0]
    html_fields = convert_to_html(md_fields)

    return html_fields


def extract_fields_cz(contents: str) -> List[str]:
    """
    Extracts cloze field from note block contents.
    """
    md_fields = [contents]
    html_fields = convert_to_html(md_fields)

    return html_fields


def convert_to_html(md_fields: List[str]) -> List[str]:
    """
    Converts markdown text to HTML.
    """
    html_fields = []
    for field in md_fields:
        md_field = markdown(field, extensions=["markdown.extensions.fenced_code"])
        html_fields.append(md_field)

    return html_fields
