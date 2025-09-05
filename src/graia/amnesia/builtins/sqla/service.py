from collections.abc import Sequence
from typing import Any, ClassVar, Literal, TypeVar, cast

from launart import Launart, Service
from loguru import logger
from sqlalchemy import Table
from sqlalchemy.engine.result import Result
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.base import Executable
from sqlalchemy.sql.selectable import TypedReturnsRows

from ..utils import get_subclasses
from .model import Base
from .types import EngineOptions

T_Row = TypeVar("T_Row", bound=DeclarativeBase)


class SqlalchemyService(Service):
    id: str = "database/sqlalchemy"
    base_class: ClassVar[type[DeclarativeBase]] = Base
    engines: dict[str, AsyncEngine]
    session_factory: async_sessionmaker[AsyncSession]

    def __init__(
        self,
        url: str | URL,
        engine_options: EngineOptions | None = None,
        session_options: dict[str, Any] | None = None,
        binds: dict[str, str | URL] | None = None,
        create_table_at: Literal["preparing", "prepared", "blocking"] = "preparing",
    ) -> None:
        if engine_options is None:
            engine_options = {"echo": "debug", "pool_pre_ping": True}
        self.engines = {"": create_async_engine(url, **engine_options)}
        for key, bind_url in (binds or {}).items():
            self.engines[key] = create_async_engine(bind_url, **engine_options)
        self.create_table_at = create_table_at
        self.session_options = session_options or {"expire_on_commit": False}
        super().__init__()

    @property
    def required(self) -> set[str]:
        return set()

    @property
    def stages(self) -> set[Literal["preparing", "blocking", "cleanup"]]:
        return {"preparing", "blocking", "cleanup"}

    async def initialize(self):
        _binds = {}
        binds = {}

        for model in set(get_subclasses(self.base_class)):
            table: Table | None = getattr(model, "__table__", None)

            if table is None or (bind_key := table.info.get("bind_key")) is None:
                continue

            if bind_key in self.engines:
                _binds[model] = self.engines[bind_key]
                binds.setdefault(bind_key, []).append(model)
            else:
                _binds[model] = self.engines[""]
                binds.setdefault("", []).append(model)

        self.session_factory = async_sessionmaker(self.engines[""], binds=_binds, **self.session_options)
        return binds

    def get_session(self, **local_kw):
        return self.session_factory(**local_kw)

    async def launch(self, manager: Launart):
        binds: dict[str, list[type[Base]]] = {}

        async with self.stage("preparing"):
            logger.info("Initializing database...")
            if self.create_table_at == "preparing":
                binds = await self.initialize()
                logger.success("Database initialized!")
                for key, models in binds.items():
                    async with self.engines[key].begin() as conn:
                        await conn.run_sync(
                            self.base_class.metadata.create_all, tables=[m.__table__ for m in models], checkfirst=True
                        )
                logger.success("Database tables created!")

        if self.create_table_at != "preparing":
            binds = await self.initialize()
            logger.success("Database initialized!")
        if self.create_table_at == "prepared":
            for key, models in binds.items():
                async with self.engines[key].begin() as conn:
                    await conn.run_sync(
                        self.base_class.metadata.create_all, tables=[m.__table__ for m in models], checkfirst=True
                    )
            logger.success("Database tables created!")

        async with self.stage("blocking"):
            if self.create_table_at == "blocking":
                for key, models in binds.items():
                    async with self.engines[key].begin() as conn:
                        await conn.run_sync(
                            self.base_class.metadata.create_all, tables=[m.__table__ for m in models], checkfirst=True
                        )
                logger.success("Database tables created!")
            await manager.status.wait_for_sigexit()
        async with self.stage("cleanup"):
            for engine in self.engines.values():
                await engine.dispose(close=True)

    async def execute(self, sql: Executable) -> Result:
        """执行 SQL 命令"""
        async with self.get_session() as session:
            return await session.execute(sql)

    async def select_all(self, sql: TypedReturnsRows[tuple[T_Row]]) -> Sequence[T_Row]:
        async with self.get_session() as session:
            result = await session.scalars(sql)
        return result.all()

    async def select_first(self, sql: TypedReturnsRows[tuple[T_Row]]) -> T_Row | None:
        async with self.get_session() as session:
            result = await session.scalars(sql)
        return cast("T_Row | None", result.first())

    async def add(self, row: Base) -> None:
        async with self.get_session() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)

    async def add_many(self, rows: Sequence[Base]):
        async with self.get_session() as session:
            session.add_all(rows)
            await session.commit()
            for row in rows:
                await session.refresh(row)

    async def update_or_add(self, row: Base):
        async with self.get_session() as session:
            await session.merge(row)
            await session.commit()
            await session.refresh(row)

    async def delete_exist(self, row: Base):
        async with self.get_session() as session:
            await session.delete(row)

    async def delete_many_exist(self, rows: Sequence[Base]):
        async with self.get_session() as session:
            for row in rows:
                await session.delete(row)
