from abc import ABCMeta, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

TJsonLiteralValue = Union[str, int, float, bool, None]
TJsonKey = Union[str, int]
TJsonStructure = Union[Dict[TJsonKey, "TJson"], List["TJson"], Tuple["TJson", ...]]
TJson = Union[TJsonLiteralValue, TJsonStructure]

TJsonCustomSerializer = Callable[[Any], TJson]

# 因为 Tuple 虽然是 Hashable & builtin & Immutable, 但是不符合 JSON 规范, 所以 Tuple 无法作为 TJsonKey.
# bytes 不必说.


class JSONBackend(metaclass=ABCMeta):
    @abstractmethod
    def serialize(self, value: TJson, *, custom_serializers: Optional[Dict[Type, TJsonCustomSerializer]] = None) -> str:
        raise NotImplementedError()

    @abstractmethod
    def deserialize(self, value: str) -> TJson:
        raise NotImplementedError()

    def serialize_as_bytes(
        self, value: Any, *, custom_serializers: Optional[Dict[Type, TJsonCustomSerializer]] = None
    ) -> bytes:
        return self.serialize(value, custom_serializers=custom_serializers).encode("utf-8")


from .bootstrap import CURRENT_BACKEND as CURRENT_BACKEND
from .frontend import Json as Json
