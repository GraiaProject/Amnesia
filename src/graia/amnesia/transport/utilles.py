from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, List, Type, TypeVar

from graia.amnesia.transport.signature import TransportSignature

if TYPE_CHECKING:
    from graia.amnesia.transport import Transport

T_TransportHandler = TypeVar("T_TransportHandler", bound=Callable)


class TransportRegistrar(Generic[T_TransportHandler]):
    handlers: Dict[TransportSignature, Callable]
    callbacks: Dict[TransportSignature, List]
    declares: List[TransportSignature[None]]

    def __init__(self) -> None:
        self.handlers = {}
        self.callbacks = {}
        self.declares = []

    def handle(self, signature: TransportSignature[T_TransportHandler]):
        def decorator(method: T_TransportHandler):
            self.handlers[signature] = method
            return method

        return decorator

    def on(self, signature: TransportSignature[T_TransportHandler]):
        def decorator(method: T_TransportHandler):
            self.callbacks.setdefault(signature, []).append(method)
            return method

        return decorator

    def declare(self, signature: TransportSignature[Any]):
        self.declares.append(signature)
        return signature

    def apply(self, transport_class: Type["Transport"]):
        transport_class.handlers.update(self.handlers)
        transport_class.callbacks.update(self.callbacks)
        transport_class.declares.extend(self.declares)
        return transport_class
