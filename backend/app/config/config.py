from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    CORS_ORGINS: list[str] = ["http://localhost:3000"]

    ANTHROPIC_API_KEY: Optional[str] = ""

    GOOGLE_API_KEY: Optional[str] = ""

settings = Settings()
