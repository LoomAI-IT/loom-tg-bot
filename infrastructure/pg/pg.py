from typing import Any, Sequence

from opentelemetry.trace import Status, StatusCode, SpanKind
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from internal import interface


def NewPool(
        db_user,
        db_pass,
        db_host
        , db_port,
        db_name
):
    async_engine = create_async_engine(
        f"postgresql+asyncpg://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}",
        echo=False,
        future=True,
        pool_size=15,
        max_overflow=15,
        pool_recycle=300
    )

    pool = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False
    )
    return pool


class PG(interface.IDB):

    def __init__(self, tel: interface.ITelemetry, db_user, db_pass, db_host, db_port, db_name):
        self.pool = NewPool(db_user, db_pass, db_host, db_port, db_name)
        self.tracer = tel.tracer()

    async def insert(self, query: str, query_params: dict) -> int:
        async with self.pool() as session:
            result = await session.execute(text(query), query_params)
            await session.commit()
            rows = result.all()
            return rows[0][0]

    async def delete(self, query: str, query_params: dict) -> None:
        async with self.pool() as session:
            await session.execute(text(query), query_params)
            await session.commit()

    async def update(self, query: str, query_params: dict) -> None:
        async with self.pool() as session:
            await session.execute(text(query), query_params)
            await session.commit()

    async def select(self, query: str, query_params: dict) -> Sequence[Any]:
        async with self.pool() as session:
            result = await session.execute(text(query), query_params)
            rows = result.all()
            return rows

    async def multi_query(
            self,
            queries: list[str]
    ) -> None:
        async with self.pool() as session:
            for query in queries:
                await session.execute(text(query))
            await session.commit()
        return None
