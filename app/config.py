from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Project settings"""

    VERSION: str = "0.1.3"
    DECK_TITLE_KEY: str = "deck"
    GUID_KEY: str = "uid"
    TAG_KEY: str = "tag"
    SOURCE_KEY: str = "src"


settings = Settings()
