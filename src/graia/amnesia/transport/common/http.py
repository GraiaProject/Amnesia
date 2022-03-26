from abc import abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    TypedDict,
    overload,
)

from typing_extensions import NotRequired, Unpack

from graia.amnesia.transport.interface import ExtraContent, TransportInterface
from graia.amnesia.transport.signature import TransportSignature


@dataclass
class HttpRequest(ExtraContent):
    headers: Dict[str, str]
    query_params: Dict[str, str]
    url: str
    host: str
    client_ip: str
    client_port: int
    cookies: Dict[str, str]


@dataclass
class HttpResponseExtra(ExtraContent):
    status: int
    headers: Dict[str, str]
    cookies: Dict[str, str]


class HttpServerRequestInterface(TransportInterface[bytes]):
    @abstractmethod
    async def receive(self) -> bytes:
        raise NotImplementedError

    async def send(self, data: Any):
        raise TypeError("use return response instead")

    @abstractmethod
    async def extra(self, signature: Any):
        raise NotImplementedError


class HttpClientResponseInterface(TransportInterface[bytes]):
    @abstractmethod
    async def receive(self) -> bytes:
        raise NotImplementedError

    async def send(self, data: bytes):
        raise TypeError("http client response can't send data")

    @abstractmethod
    async def extra(self, signature: Any):
        raise NotImplementedError


class WebsocketInterface(TransportInterface[bytes]):
    @abstractmethod
    async def receive(self) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def send(self, data: bytes):
        raise NotImplementedError

    @overload
    @abstractmethod
    async def extra(self, signature: Literal["accept"]) -> None:
        ...

    @overload
    @abstractmethod
    async def extra(self, signature: Literal["close"]) -> None:
        ...

    @abstractmethod
    async def extra(self, signature: Any):
        raise NotImplementedError


def status(code: int):
    return {"status": code}


def headers(headers: Dict[str, str]):
    return {"headers": headers}


def cookies(cookies: Dict[str, str], expires: Optional[int] = None):
    return {"cookies": cookies, "cookie_expires": expires}


class HttpServerResponse(TypedDict):
    status: NotRequired[int]
    headers: NotRequired[Dict[str, str]]
    cookies: NotRequired[Dict[str, str]]
    cookie_expires: NotRequired[Optional[int]]


class response:
    body: Any
    description: HttpServerResponse

    def __init__(self, response_body: Any, *desc: Dict[str, Any]):
        self.body = response_body
        self.description = {}
        for i in desc:
            self.description.update(i)  # type: ignore


class http:
    @dataclass
    class Endpoint(
        TransportSignature[
            Callable[
                [TransportInterface[bytes]],
                "Tuple[Any, Unpack[Tuple[Dict[str, Any], ...]]] | Any",
            ]
        ]
    ):
        path: str
        method: List[Literal["GET", "POST", "PUT", "DELETE"]] = field(default_factory=lambda: ["GET"])  # type: ignore

    @dataclass
    class WebsocketEndpoint(
        Endpoint,
        TransportSignature[Callable[[WebsocketInterface], None]],
    ):
        method: Final[str] = "WS"
