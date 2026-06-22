from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

DATABASE_URL = "sqlite+aiosqlite:///./local_dev.db"

engine = create_async_engine(DATABASE_URL, echo=True)

SessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    async with SessionLocal() as session:
        yield session


async def init_db():
    print("✅ INIT DB CALLED")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✅ TABLES CREATED:", Base.metadata.tables.keys())
