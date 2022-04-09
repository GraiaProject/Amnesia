from functools import partial
from typing import Callable, Dict, List, Optional, TypeVar, cast

from graia.amnesia.transport.signature import TransportSignature

T = TypeVar("T", bound=Callable)

# TODO: 连接内简易触发器, 用于通知错误之类的, 或者是 req-res on ws 这种模式上的.
class Transport:
    handlers: Dict[TransportSignature, Callable] = {}
    callbacks: Dict[TransportSignature, List] = {}
    declares: List[TransportSignature[None]] = []

    @classmethod
    def __init_subclass__(cls, **kwargs) -> None:
        cls.handlers = {}
        cls.callbacks = {}
        cls.declares = []
        for base in reversed(cls.__bases__):
            if issubclass(base, Transport):
                cls.handlers.update(base.handlers)
                cls.callbacks.update(base.callbacks)
                cls.declares.extend(base.declares)

    def get_handler(self, signature: TransportSignature[T]) -> T:
        handler = cast(Optional[T], self.handlers.get(signature))
        if not handler:
            raise TypeError(f"{self.__class__.__name__} has no handler for {signature}")
        return partial(handler, self)  # type: ignore

    def get_callbacks(self, signature: TransportSignature[T]) -> List[T]:
        callbacks = cast(Optional[List[T]], self.callbacks.get(signature))
        if not callbacks:
            raise TypeError(f"{self.__class__.__name__} has no callback for {signature}")
        return [partial(callback, self) for callback in callbacks]  # type: ignore

    def has_handler(self, signature: TransportSignature[T]) -> bool:
        return signature in self.handlers

    def has_callback(self, signature: TransportSignature[T]) -> bool:
        return signature in self.callbacks

    def iter_handlers(self):
        for signature, unbound in self.handlers.items():
            yield signature, partial(unbound, self)

    def iter_callbacks(self):
        for signature, unbound_callbacks in self.callbacks.items():
            yield signature, [partial(callback, self) for callback in unbound_callbacks]
