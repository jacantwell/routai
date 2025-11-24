from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    GOOGLE_ROUTES_API_ENDPOINT: str = "https://routes.googleapis.com/directions/v2:computeRoutes"

    GOOGLE_GEOCODING_API_ENDPOINT: str = "https://maps.googleapis.com/maps/api/geocode/json"

    GOOGLE_PLACES_API_ENDPOINT: str = "https://places.googleapis.com/v1/places:searchNearby"

    CORS_ORGINS: list[str] = ["http://localhost:3000"]

    ANTHROPIC_API_KEY: Optional[str] = ""

    GOOGLE_API_KEY: Optional[str] = ""

settings = Settings()
