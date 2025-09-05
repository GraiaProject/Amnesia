from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.schema import Table

_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


_callbacks = []


def register_callback(callback: Callable[[type["Base"], dict[str, Any]], Any]) -> None:
    """
    Register a callback to be called when a new Base subclass is created.
    """
    _callbacks.append(callback)


def remove_callback(callback: Callable[[type["Base"], dict[str, Any]], Any]) -> None:
    """
    Remove a previously registered callback.
    """
    if callback in _callbacks:
        _callbacks.remove(callback)


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True
    metadata = MetaData(naming_convention=_NAMING_CONVENTION)

    if TYPE_CHECKING:
        __table__: ClassVar[Table]  # type: ignore

    def __init_subclass__(cls, **kwargs):
        for callback in _callbacks:
            callback(cls, kwargs)

        if not hasattr(cls, "__tablename__") and "tablename" in kwargs:
            cls.__tablename__ = kwargs["tablename"]
        if not hasattr(cls, "__table_args__") and "table_args" in kwargs:
            cls.__table_args__ = kwargs["table_args"]
        if not hasattr(cls, "__mapper__") and "mapper" in kwargs:
            cls.__mapper__ = kwargs["mapper"]
        if not hasattr(cls, "__mapper_args__") and "mapper_args" in kwargs:
            cls.__mapping_args__ = kwargs["mapper_args"]

        super().__init_subclass__()

        if not hasattr(cls, "__table__"):
            return

        bind_key: str | None = getattr(cls, "__bind_key__", kwargs.get("bind_key", None))

        if bind_key is None:
            bind_key = ""

        cls.__table__.info["bind_key"] = bind_key
