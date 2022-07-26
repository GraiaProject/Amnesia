from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from typing_extensions import Concatenate, ParamSpec

from graia.amnesia.transport import Transport
from graia.amnesia.transport.signature import TransportSignature

P_TransportHandler = ParamSpec("P_TransportHandler")

T_Transport = TypeVar("T_Transport", bound="Transport")


class TransportRegistrar:
    handlers: dict[TransportSignature, Callable]
    callbacks: dict[TransportSignature, list]
    declares: list[TransportSignature[None]]

    def __init__(self) -> None:
        self.handlers = {}
        self.callbacks = {}
        self.declares = []

    def handle(self, signature: TransportSignature[Callable[P_TransportHandler, Any]]):
        def decorator(
            method: Callable[Concatenate[T_Transport, P_TransportHandler], Any]
        ) -> Callable[Concatenate[T_Transport, P_TransportHandler], Any]:
            self.handlers[signature] = method
            return method

        return decorator

    def on(self, signature: TransportSignature[Callable[P_TransportHandler, Any]]):
        def decorator(
            method: Callable[Concatenate[T_Transport, P_TransportHandler], Any]
        ) -> Callable[Concatenate[T_Transport, P_TransportHandler], Any]:
            self.callbacks.setdefault(signature, []).append(method)
            return method

        return decorator

    def declare(self, signature: TransportSignature[Any]):
        self.declares.append(signature)
        return signature

    def apply(self, transport_class: type[T_Transport]) -> type[T_Transport]:
        transport_class.handlers.update(self.handlers)
        transport_class.callbacks.update(self.callbacks)
        transport_class.declares.extend(self.declares)
        return transport_class
