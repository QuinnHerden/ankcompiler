from dataclasses import dataclass
from pathlib import Path
from typing import List

from genanki.model import Model

from app.config import settings
from app.logic.sources import File, NoteType
from app.logic.utils import convert_md_to_html


@dataclass
class Block:
    meta_str: str
    body_str: str
    file: "File"

    def extract_note(self) -> Note:
        """Extracts a note from a note block."""

        meta_dict = self._extract_meta()

        guid = meta_dict.get(settings.GUID_KEY)
        tags = meta_dict.get(settings.TAG_KEY)

        if guid is None:
            raise ValueError("No guid found in note meta block")

        model = self._extract_type().model
        fields = self._extract_fields()

        meta_tags = self.file.get_tags()

        tags.extend(meta_tags)
        tags = list(dict.fromkeys(tags))

        images = self._extract_images()

        note = Note(
            guid=guid,
            model=model,
            fields=fields,
            tags=tags,
            source=self.file,
            images=images,
        )

        return note

    def _extract_meta(self) -> dict:
        """
        Extracts metadata from note block.
        """
        meta_dict = {settings.GUID_KEY: None, settings.TAG_KEY: []}

        matches = re.findall(r"(\[\^(\w+)\]: *(.+))", self.meta_str)

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

    def _extract_type(self) -> NoteType:
        """Classifies note block into a note type."""
        types = get_types()

        matches = []
        for type_ in types:
            match = re.compile(type_.regex, re.DOTALL).findall(self.body_str)
            if len(match) > 0:
                matches.append(type_)

        if len(matches) == 0:
            raise ValueError("Could not find a note type for block")

        if len(matches) > 1:
            raise ValueError("Found more than one note type for block")

        return matches[0]

    def _extract_fields(self) -> List[str]:
        """
        Extracts fields from note block.
        """
        note_type = self._extract_type()

        matches = re.compile(note_type.regex, re.DOTALL).findall(self.body_str)

        if len(matches) != 1:
            raise ValueError("Could not extract content from block")

        elif isinstance(matches[0], tuple):  # need to unpack (['…', '…'])
            md_fields = list(matches[0])

        elif isinstance(matches, list):  # already in correct format ['…']
            md_fields = matches

        html_fields = convert_md_to_html(md_fields)

        return html_fields

    def _extract_images(self) -> List[Path]:
        """Extracts image paths from note block."""
        image_paths = []
        return image_paths
