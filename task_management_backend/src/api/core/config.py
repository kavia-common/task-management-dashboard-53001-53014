import os
from dataclasses import dataclass


def _build_postgres_url_from_parts() -> str | None:
    """
    Build a postgres URL from the database container-style env vars.

    Expected env vars (as provided by the DB container metadata):
      - POSTGRES_USER
      - POSTGRES_PASSWORD
      - POSTGRES_DB
      - POSTGRES_PORT
    We assume the host is `localhost` within the workspace networking model.
    """
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("POSTGRES_DB")
    port = os.getenv("POSTGRES_PORT")

    if not (user and password and db and port):
        return None

    return f"postgresql://{user}:{password}@localhost:{port}/{db}"


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
    - JWT_SECRET_KEY: secret key used to sign JWTs (MUST be set in .env by orchestrator)

    Database configuration (either is acceptable):
    - POSTGRES_URL: full postgres URL (e.g. postgresql://host:port/db)
      OR
    - POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT:
      DB container-style variables used to construct a URL.

    Returns:
        Settings: validated settings object.

    Raises:
        RuntimeError: if a required environment variable is missing.
    """
    postgres_url = os.getenv("POSTGRES_URL") or _build_postgres_url_from_parts()
    if not postgres_url:
        raise RuntimeError(
            "Missing database configuration. Set POSTGRES_URL or set "
            "POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_DB/POSTGRES_PORT."
        )

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
