from typing import Callable, Dict, List, TypeVar

from graia.amnesia.transport.signature import TransportSignature

T = TypeVar("T")


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
