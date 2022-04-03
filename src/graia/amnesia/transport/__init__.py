from functools import partial
from typing import Callable, Dict, List, Optional, TypeVar, cast

from graia.amnesia.transport.signature import TransportSignature

T = TypeVar("T", contravariant=True, bound=Callable)


class Transport:
    handlers: Dict[TransportSignature, Callable] = {}
    callbacks: Dict[TransportSignature, List] = {}

    def __init_subclass__(cls, **kwargs) -> None:
        cls.handlers = {}
        cls.callbacks = {}
        for base in reversed(cls.__bases__):
            if issubclass(base, Transport):
                cls.handlers.update(base.handlers)
                cls.callbacks.update(base.callbacks)

    def get_handler(self, signature: TransportSignature[T]) -> Optional[T]:
        handler = cast(Optional[T], self.handlers.get(signature))
        if handler:
            handler = partial(handler, self)
        return handler  # type: ignore

    def get_callbacks(self, signature: TransportSignature[T]) -> Optional[List[T]]:
        callbacks = cast(Optional[List[T]], self.callbacks.get(signature))
        if callbacks:
            callbacks = [partial(callback, self) for callback in callbacks]
        return callbacks  # type: ignore
