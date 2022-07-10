from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, List, Literal, Optional

from launart.service import ExportInterface, TService

from graia.amnesia.json import TJson
from graia.amnesia.transport.common.http.io import AbstractServerRequestIO
from graia.amnesia.transport.common.http.responses import T_HttpResponse
from graia.amnesia.transport.rider import TransportRider
from graia.amnesia.transport.signature import TransportSignature


@dataclass
class HttpEndpoint(
    TransportSignature[
        Callable[
            [AbstractServerRequestIO],
            Coroutine[None, None, T_HttpResponse],
        ]
    ]
):
    path: str
    methods: List[Literal["GET", "POST", "PUT", "DELETE"]] = field(default_factory=lambda: ["GET"])

    def __hash__(self) -> int:
        return hash(self.path) + hash(id(self.methods))


class AbstractClientInterface(ExportInterface[TService], metaclass=ABCMeta):
    @abstractmethod
    def __init__(self, service: TService) -> None:
        raise NotImplementedError

    @abstractmethod
    def request(
        self,
        method: str,
        url: str,
        params: Optional[dict] = None,
        data: Optional[Any] = None,
        headers: Optional[dict] = None,
        cookies: Optional[dict] = None,
        timeout: Optional[float] = None,
        *,
        json: Optional[TJson] = None,
        **kwargs: Any,
    ) -> TransportRider:
        raise NotImplementedError

    def websocket(self, url: str, **kwargs) -> TransportRider:
        raise NotImplementedError
