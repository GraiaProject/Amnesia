import typing
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, Generic, Type, TypeVar
from uuid import UUID

T = TypeVar("T")


class _AmnesiaJsonCustomSerialize(Generic[T], Dict[Type[T], Callable[[T], Any]]):
    def new(self, t: Type[T]):
        def decorator(func: Callable[[T], Any]):
            self[t] = func
            return func

        return decorator


SERIALIZERS = _AmnesiaJsonCustomSerialize()

SERIALIZE_UUID_USING_HEX = False
SERIALIZE_DECIMAL_AS_STR = True


def SERIALIZER_DEFAULT(v, d: Dict[Any, Callable[[Any], Any]] = SERIALIZERS):
    return d[v.__class__](v) if v.__class__ in d else v


@SERIALIZERS.new(datetime)
def _(dt: datetime) -> str:
    return dt.isoformat()


@SERIALIZERS.new(timedelta)
def _(td: timedelta) -> str:
    return str(td)


@SERIALIZERS.new(tuple)
def _(t: tuple) -> list:
    return list(t)


@SERIALIZERS.new(set)
def _(s: set) -> list:
    return list(s)


@SERIALIZERS.new(date)
def _(d: date) -> str:
    return d.isoformat()


@SERIALIZERS.new(time)
def _(t: time) -> str:
    return t.isoformat()


@SERIALIZERS.new(Decimal)
def _(d: Decimal):
    return str(d) if SERIALIZE_DECIMAL_AS_STR else float(d)


@SERIALIZERS.new(UUID)
def _(u: UUID) -> str:
    return u.hex if SERIALIZE_UUID_USING_HEX else str(u)


@SERIALIZERS.new(typing.TypedDict)
def _(t: typing.TypedDict) -> dict:
    return dict(t)


@SERIALIZERS.new(typing.NamedTuple)
def _(t: typing.NamedTuple) -> dict:
    return dict(t._asdict())


@SERIALIZERS.new(Enum)
def _(e: Enum) -> str:
    return e.value
