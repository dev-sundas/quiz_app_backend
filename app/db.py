from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.config import settings
from typing import AsyncGenerator

db_url_str = settings.get_db_url()

engine = create_async_engine(db_url_str, echo=True, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

import asyncio
import asyncpg

DATABASE_URL = "postgresql+asyncpg://postgres:PASSWORD@postgres-6j0z.railway.internal:5432/railway"

async def connect_db(retries=5, delay=3):
    for i in range(retries):
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            print("DB connected!")
            return conn
        except Exception as e:
            print(f"DB not ready, retrying {i+1}/{retries}...", e)
            await asyncio.sleep(delay)
    raise Exception("Could not connect to DB after retries")

# Example usage
asyncio.run(connect_db())
