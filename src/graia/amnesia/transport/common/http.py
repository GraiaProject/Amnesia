from abc import abstractmethod
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
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
    Union,
    overload,
)

from typing_extensions import NotRequired, Unpack

from graia.amnesia.transport.interface import (
    ExtraContent,
    PacketIO,
    ReadonlyIO,
    TransportIO,
)
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


HttpResponse = Union[Tuple[Any, Unpack[Tuple[Dict[str, Any], ...]]], Any]


class HttpServerRequestInterface(ReadonlyIO[bytes]):
    @abstractmethod
    async def read(self) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def extra(self, signature: Any):
        raise NotImplementedError

    async def headers(self) -> Dict[str, str]:
        req = await self.extra(HttpRequest)  # type: HttpRequest
        return req.headers

    async def cookies(self) -> Dict[str, str]:
        req = await self.extra(HttpRequest)  # type: HttpRequest
        return req.cookies


class HttpClientResponseInterface(ReadonlyIO[bytes]):
    @abstractmethod
    async def read(self) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def extra(self, signature: Any):
        raise NotImplementedError

    async def headers(self) -> Dict[str, str]:
        req = await self.extra(HttpRequest)  # type: HttpRequest
        return req.headers

    async def cookies(self) -> Dict[str, str]:
        req = await self.extra(HttpRequest)  # type: HttpRequest
        return req.cookies


class WebsocketInterface(PacketIO[bytes]):
    @abstractmethod
    async def receive(self) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def send(self, data: bytes):
        raise NotImplementedError

    @abstractmethod
    async def extra(self, signature: Any):
        raise NotImplementedError

    async def close(self):
        if not self.closed:
            await self.extra(websocket.close)


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
                [HttpServerRequestInterface],
                HttpResponse,
            ]
        ]
    ):
        path: str
        method: List[Literal["GET", "POST", "PUT", "DELETE"]] = field(default_factory=lambda: ["GET"])  # type: ignore

    @dataclass
    class WsEndpoint(
        Endpoint,
        TransportSignature[Callable[[WebsocketInterface], None]],
    ):
        method: Final[str] = "WS"


class websocket:
    accept = TransportSignature[None]()
    close = TransportSignature[None]()
