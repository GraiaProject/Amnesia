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
