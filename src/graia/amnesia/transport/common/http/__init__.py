from dataclasses import dataclass, field
from typing import Callable, Coroutine, List, Literal

from graia.amnesia.transport.common.http.io import AbstractServerRequestIO
from graia.amnesia.transport.common.http.responses import T_HttpResponse
from graia.amnesia.transport.signature import TransportSignature


@dataclass
class endpoint(
    TransportSignature[
        Callable[
            [AbstractServerRequestIO],
            Coroutine[None, None, T_HttpResponse],
        ]
    ]
):
    path: str
    methods: List[Literal["GET", "POST", "PUT", "DELETE"]] = field(default_factory=lambda: ["GET"])