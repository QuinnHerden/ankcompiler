"""Golden test for the genanki note models.

Anki matches an imported note to an existing user's note type by model id, and
expects the same fields and templates. Changing any of these silently forks or
breaks users' collections, so every value is pinned here on purpose. Update this
test only alongside a deliberate, documented model migration.
"""

from genanki.model import Model

from app.logic.sources import NoteType

CSS = '@import url("_stylesheet.css");'

EXPECTED = {
    "qa": {
        "model_id": "1764365620",
        "name": "AnkCompiler-Question_Answer",
        "model_type": Model.FRONT_BACK,
        "fields": ["Question", "Answer", "Source"],
        "templates": [
            {
                "name": "QA",
                "qfmt": "{{Question}}",
                "afmt": "{{Question}}<hr id=answer>{{Answer}}",
            },
        ],
        "css": CSS,
    },
    "cloze": {
        "model_id": "1783507665",
        "name": "AnkCompiler-Cloze",
        "model_type": Model.CLOZE,
        "fields": ["Text", "Source"],
        "templates": [
            {
                "name": "Cloze",
                "qfmt": "{{cloze:Text}}",
                "afmt": "{{cloze:Text}}",
            },
        ],
        "css": CSS,
    },
    "reversed": {
        "model_id": "1764365630",
        "name": "AnkCompiler-Basic-Reversed",
        "model_type": Model.FRONT_BACK,
        "fields": ["Front", "Back", "Source"],
        "templates": [
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
        "css": CSS,
    },
    "type-in": {
        "model_id": "1764365640",
        "name": "AnkCompiler-Type-In",
        "model_type": Model.FRONT_BACK,
        "fields": ["Question", "Answer", "Source"],
        "templates": [
            {
                "name": "Type-In",
                "qfmt": "{{Question}}<br>{{type:Answer}}",
                "afmt": "{{Question}}<hr id=answer>{{Answer}}",
            },
        ],
        "css": CSS,
    },
}


def _snapshot(model: Model) -> dict:
    return {
        "model_id": model.model_id,
        "name": model.name,
        "model_type": model.model_type,
        "fields": [field["name"] for field in model.fields],
        "templates": model.templates,
        "css": model.css,
    }


def test_note_models_are_pinned():
    actual = {t.key: _snapshot(t.model) for t in NoteType.get_types()}
    assert actual == EXPECTED
