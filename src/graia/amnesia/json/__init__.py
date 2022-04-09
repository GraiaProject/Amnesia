from abc import ABCMeta, abstractmethod
from typing import Any, Callable, Dict, List, Tuple, Type, Union

TJsonLiteralValue = Union[str, int, float, bool, None]
TJsonKey = Union[str, int]
TJsonStructure = Union[Dict[TJsonKey, "TJson"], List["TJson"], Tuple["TJson", ...]]
TJson = Union[TJsonLiteralValue, TJsonStructure]

TJsonCustomSerializer = Callable[[Any], TJson]

# 因为 Tuple 虽然是 Hashable & builtin & Immutable, 但是不符合 JSON 规范, 所以 Tuple 无法作为 TJsonKey.
# bytes 不必说.


class JSONBackend(metaclass=ABCMeta):
    @abstractmethod
    def dumps(self, value: TJson, *, defaults: Dict[Type, TJsonCustomSerializer]) -> str:
        raise NotImplementedError()

    @abstractmethod
    def loads(self, value: str) -> TJson:
        raise NotImplementedError()
