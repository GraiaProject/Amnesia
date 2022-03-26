from typing import TYPE_CHECKING, Any, Callable, Dict, List, Type, TypeVar

from graia.amnesia.transport.signature import TransportSignature

if TYPE_CHECKING:
    from graia.amnesia.transport import Transport

T_TransportHandler = TypeVar("T_TransportHandler", bound=Callable)


class HandlerRegistrar(
    Dict[TransportSignature[T_TransportHandler], T_TransportHandler]
):
    def signature(self, signature: TransportSignature[T_TransportHandler]):
        def decorator(method: T_TransportHandler):
            self[signature] = method
            return method

        return decorator

    def apply(self, transport_class: Type[Transport]):
        transport_class.handlers.update(self)
        return transport_class


class CallbackRegistrar(
    Dict[TransportSignature[T_TransportHandler], List[T_TransportHandler]]
):
    def signature(self, signature: TransportSignature[T_TransportHandler]):
        def decorator(method: T_TransportHandler):
            self.setdefault(signature, []).append(method)
            return method

        return decorator

    def apply(self, transport_class: Type[Transport]):
        transport_class.callbacks.update(self)
        return transport_class
