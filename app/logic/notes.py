from enum import Enum, auto

from genanki.model import Model


class NoteType(Enum):
    """Types of Anki notes"""

    QUESTION_ANSWER = auto()
    FRONT_BACK = auto()
    CLOZE = auto()


def get_model_qa() -> Model:
    """Get model for Question-Answer Anki notes."""
    return Model(
        model_id=NoteType.QUESTION_ANSWER.value,
        name=NoteType.QUESTION_ANSWER.name,
        fields=[{"name": "Question"}, {"name": "Answer"}],
        templates=[
            {
                "name": NoteType.QUESTION_ANSWER.name,
                "qfmt": '<div class="card">'
                + '<div class="question">{{Question}}</div>'
                + "</div>",
                "afmt": '<div class="card">'
                + '<div class="question">{{Question}}</div>'
                + "<hr>"
                + '<div class="answer">{{Answer}}</div>'
                + "</div>",
            },
        ],
        model_type=Model.FRONT_BACK,
    )


def get_model_fb() -> Model:
    """Get model for Front-Back Anki notes."""
    return Model(
        model_id=NoteType.FRONT_BACK.value,
        name=NoteType.FRONT_BACK.name,
        fields=[{"name": "Front"}, {"name": "Back"}],
        templates=[
            {
                "name": NoteType.FRONT_BACK.name,
                "qfmt": '<div class="card">'
                + '<div class="front">{{Front}}</div>'
                + "</div>",
                "afmt": '<div class="card">'
                + '<div class="back">{{Back}}</div>'
                + "</div>",
            },
        ],
        model_type=Model.FRONT_BACK,
    )


def get_model_cz() -> Model:
    """Get model for Cloze Anki notes."""

    return Model(
        model_id=NoteType.CLOZE.value,
        name=NoteType.CLOZE.name,
        fields=[{"name": "Cloze"}],
        templates=[
            {
                "name": NoteType.CLOZE.name,
                "qfmt": '<div class="card">'
                + '<div class="cloze">{{cloze:Cloze}}</div>'
                + "</div>",
                "afmt": '<div class="card">'
                + '<div class="question">{{cloze:Cloze}}</div>',
            },
        ],
        model_type=Model.CLOZE,
    )
