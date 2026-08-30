from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    live_provider: str = "gemini"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    exa_api_key: str = ""
    apify_token: str = ""
    apify_actor: str = "compass/crawler-google-places"
    guava_api_key: str = ""
    guava_agent_number: str = ""
    guava_webrtc_code: str = ""
    # Dev/hackathon: the number the mocked trade search hands back, so the
    # "shop" is something that can actually answer. Replaces the old dial-time
    # redirect, which made the UI name one shop while a different phone rang.
    homeops_dev_shop_phone: str = ""
    # Dialling a real phone must be switched on deliberately. Anything that
    # forgets to set this - a test run, a stray script, a fresh clone - gets a
    # labelled mock instead of ringing somebody.
    homeops_allow_real_calls: bool = False
    # Refuse to dial the same number twice inside this window. A runaway loop
    # rings once, not thirty times.
    homeops_call_cooldown_seconds: int = 60
    homeowner_name: str = ""
    database_url: str = (
        "postgresql+asyncpg://homeops:homeops@localhost:5434/homeops"
    )
    port: int = 8000
    homeops_mock: bool = False


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Managed Postgres (Render, Heroku, ...) hands out a bare postgresql:// URL.
    # SQLAlchemy needs the driver named, and app/db.py swaps asyncpg for psycopg
    # to build the blocking engine, so normalise it here in one place.
    url = settings.database_url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    settings.database_url = url
    return settings
