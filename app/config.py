from pathlib import Path

import toml
from pydantic_settings import BaseSettings

# Load the pyproject.toml file
pyproject_path = Path("pyproject.toml")
with open(pyproject_path, "r", encoding="utf-8") as f:
    pyproject_data = toml.load(f)


class Settings(BaseSettings):
    """Project settings"""

    VERSION: str = pyproject_data["project"]["version"]
    DECK_TITLE_KEY: str = "deck"
    GUID_KEY: str = "id"
    SOURCE_KEY: str = "source"


settings = Settings()
