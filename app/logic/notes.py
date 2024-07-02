from enum import Enum, auto

from genanki.model import Model


class NoteType(Enum):
    """Types of Anki notes"""

    QUESTION_ANSWER = auto()
    CLOZE = auto()


def get_model_qa() -> Model:
    """Get model for Question-Answer Anki notes."""
    return Model(
        model_id="1764365620",
        name="AnkCompiler-Question_Answer",
        fields=[{"name": "Question"}, {"name": "Answer"}],
        templates=[
            {
                "name": "QA",
                "qfmt": "{{Question}}",
                "afmt": "{{Question}}" + "<hr id=answer>" + "{{Answer}}",
            },
        ],
        css=get_default_css(),
        model_type=Model.FRONT_BACK,
    )


def get_model_cz() -> Model:
    """Get model for Cloze Anki notes."""

    return Model(
        model_id="1783507665",
        name="AnkCompiler-Cloze",
        fields=[{"name": "Text"}],
        templates=[
            {
                "name": "Cloze",
                "qfmt": "{{cloze:Text}}",
                "afmt": "{{cloze:Text}}",
            },
        ],
        css=get_default_css(),
        model_type=Model.CLOZE,
    )


def get_default_css() -> str:
    """Get default CSS."""
    return '@import url("_stylesheet.css");\n.nightMode {};'
