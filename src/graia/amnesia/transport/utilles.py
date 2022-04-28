from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, List, Type, TypeVar

from typing_extensions import Concatenate, ParamSpec

from graia.amnesia.transport.signature import TransportSignature

if TYPE_CHECKING:
    from graia.amnesia.transport import Transport


P_TransportHandler = ParamSpec("P_TransportHandler")

R_TransportHandler = TypeVar("R_TransportHandler")

T_Transport = TypeVar("T_Transport", bound="Transport")


class TransportRegistrar:
    handlers: Dict[TransportSignature, Callable]
    callbacks: Dict[TransportSignature, List]
    declares: List[TransportSignature[None]]

    def __init__(self) -> None:
        self.handlers = {}
        self.callbacks = {}
        self.declares = []

    def handle(self, signature: TransportSignature[Callable[P_TransportHandler, R_TransportHandler]]):
        def decorator(method: Callable[Concatenate[T_Transport, P_TransportHandler], R_TransportHandler]):
            self.handlers[signature] = method
            return method

        return decorator

    def on(self, signature: TransportSignature[Callable[P_TransportHandler, R_TransportHandler]]):
        def decorator(method: Callable[Concatenate[T_Transport, P_TransportHandler], R_TransportHandler]):
            self.callbacks.setdefault(signature, []).append(method)
            return method

        return decorator

    def declare(self, signature: TransportSignature[Any]):
        self.declares.append(signature)
        return signature

    def apply(self, transport_class: Type["T_Transport"]):
        transport_class.handlers.update(self.handlers)
        transport_class.callbacks.update(self.callbacks)
        transport_class.declares.extend(self.declares)
        return transport_class
