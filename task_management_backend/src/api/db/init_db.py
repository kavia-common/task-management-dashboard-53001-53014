from sqlalchemy.ext.asyncio import AsyncEngine

from src.api.db.models import Base


# PUBLIC_INTERFACE
async def init_db(engine: AsyncEngine) -> None:
    """Initialize database schema (create tables if they don't exist)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
