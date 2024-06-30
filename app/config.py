
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Project settings"""

    VERSION: str = "0.1.3"
    DECK_TITLE_KEY: str = "deck"
    GUID_KEY: str = "id"
    SOURCE_KEY: str = "source"


settings = Settings()
