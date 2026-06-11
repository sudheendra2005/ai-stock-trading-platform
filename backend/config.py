from pydantic_settings import BaseSettings
import os


DEFAULT_DATABASE_URL = (
    "sqlite:////tmp/sql_app.db" if os.getenv("VERCEL") else "sqlite:///./sql_app.db"
)

def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

class Settings(BaseSettings):
    DATABASE_URL: str = DEFAULT_DATABASE_URL
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = {"env_file": ".env"}

settings = Settings()
settings.DATABASE_URL = normalize_database_url(settings.DATABASE_URL)
