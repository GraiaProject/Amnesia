from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Type, TypeVar

from graia.amnesia.json import TJson
from graia.amnesia.json.frontend import Json

if TYPE_CHECKING:
    from graia.amnesia.transport.common.websocket.io import AbstractWebsocketIO


T = TypeVar("T", bytes, str)


def data_type(type: Type[T], error: bool = False):
    def decorator(func: Callable[[Any, "AbstractWebsocketIO", T], Any]):
        @wraps(func)
        async def wrapper(self, io, data: Any):
            if isinstance(data, type):
                return await func(self, io, data)
            elif error:
                raise TypeError(f"Expected {type.__name__}, got {data.__class__.__name__}")

        return wrapper

    return decorator


def json_require(func: Callable[[Any, "AbstractWebsocketIO", TJson], Any]):
    @wraps(func)
    async def wrapper(self, io, data: str):
        return await func(self, io, Json.deserialize(data))

    return wrapper
