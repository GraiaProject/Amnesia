from functools import wraps
from typing import TYPE_CHECKING, Any, AnyStr, Callable, Type, TypeVar

from graia.amnesia.json import TJson
from graia.amnesia.json.frontend import Json

if TYPE_CHECKING:
    from graia.amnesia.transport.common.websocket.io import AbstractWebsocketIO


_S = TypeVar("_S")
_R = TypeVar("_R")


def data_type(type: Type[AnyStr], error: bool = False):
    def decorator(func: Callable[[Any, "AbstractWebsocketIO", AnyStr], Any]):
        @wraps(func)
        async def wrapper(self, io, data: Any):
            if isinstance(data, type):
                return await func(self, io, data)
            elif error:
                raise TypeError(f"Expected {type.__name__}, got {data.__class__.__name__}")

        return wrapper

    return decorator


def json_require(
    func: Callable[[_S, "AbstractWebsocketIO", TJson], _R]
) -> Callable[[_S, "AbstractWebsocketIO", str], _R]:
    @wraps(func)
    def wrapper(self: _S, io, data: str) -> _R:
        return func(self, io, Json.deserialize(data))

    return wrapper
