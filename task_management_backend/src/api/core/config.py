import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    # Database
    postgres_url: str

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Load and validate required settings from environment variables.

    Required environment variables:
    - POSTGRES_URL: base postgres URL (e.g. postgresql://host:port/db)
    - JWT_SECRET_KEY: secret key used to sign JWTs (MUST be set in .env by orchestrator)

    Returns:
        Settings: validated settings object.

    Raises:
        RuntimeError: if a required environment variable is missing.
    """
    postgres_url = os.getenv("POSTGRES_URL")
    if not postgres_url:
        raise RuntimeError("Missing required environment variable POSTGRES_URL")

    jwt_secret_key = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret_key:
        raise RuntimeError("Missing required environment variable JWT_SECRET_KEY")

    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    expire = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
    access_token_expire_minutes = int(expire) if expire else 60 * 24

    return Settings(
        postgres_url=postgres_url,
        jwt_secret_key=jwt_secret_key,
        jwt_algorithm=jwt_algorithm,
        access_token_expire_minutes=access_token_expire_minutes,
    )
