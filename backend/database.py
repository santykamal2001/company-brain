from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Run on startup: ensure AGE extension exists and create the graph."""
    async with engine.begin() as conn:
        # Enable Apache AGE extension
        await conn.execute(
            __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS age;")
        )
        await conn.execute(
            __import__("sqlalchemy").text("LOAD 'age';")
        )
        await conn.execute(
            __import__("sqlalchemy").text(
                "SET search_path = ag_catalog, '$user', public;"
            )
        )
        # Create the graph if it doesn't exist (create_graph errors if already exists)
        try:
            await conn.execute(
                __import__("sqlalchemy").text(
                    f"SELECT * FROM ag_catalog.create_graph('{settings.age_graph_name}');"
                )
            )
        except Exception:
            pass  # Graph already exists — safe to ignore
