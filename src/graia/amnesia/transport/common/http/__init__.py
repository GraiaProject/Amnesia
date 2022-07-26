from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Literal

from graia.amnesia.transport.common.http.io import AbstractServerRequestIO
from graia.amnesia.transport.common.http.responses import T_HttpResponse
from graia.amnesia.transport.signature import TransportSignature


@dataclass
class HttpEndpoint(TransportSignature["Callable[[AbstractServerRequestIO], Coroutine[None, None, T_HttpResponse]]"]):
    path: str
    methods: list[Literal["GET", "POST", "PUT", "DELETE"]] = field(default_factory=lambda: ["GET"])

    def __hash__(self) -> int:
        return hash(self.path) + hash(id(self.methods))
