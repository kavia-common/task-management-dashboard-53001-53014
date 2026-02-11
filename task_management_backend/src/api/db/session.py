from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.api.core.config import get_settings


def _to_async_sqlalchemy_url(url: str) -> str:
    """Convert postgres URL into an async SQLAlchemy URL (asyncpg)."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    # Support "postgres://" alias just in case.
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


settings = get_settings()

engine: AsyncEngine = create_async_engine(
    _to_async_sqlalchemy_url(settings.postgres_url),
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# PUBLIC_INTERFACE
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a DB session and ensures it is closed."""
    async with AsyncSessionLocal() as session:
        yield session
