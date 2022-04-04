import contextlib
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
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

import yarl
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
    url: yarl.URL
    host: str
    client_ip: str
    client_port: int
    cookies: Dict[str, str]


@dataclass
class HttpResponse(ExtraContent):
    status: int
    headers: Dict[str, str]
    cookies: Dict[str, str]
    uri: yarl.URL


T_HttpResponse = Union[Tuple[Any, Unpack[Tuple[Dict[str, Any], ...]]], Any]


class AbstractServerRequestIO(ReadonlyIO[bytes]):
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


class AbstactClientRequestIO(ReadonlyIO[bytes]):
    @abstractmethod
    async def read(self) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def extra(self, signature: Any):
        raise NotImplementedError

    async def headers(self) -> Dict[str, str]:
        req = await self.extra(HttpResponse)  # type: HttpResponse
        return req.headers

    async def cookies(self) -> Dict[str, str]:
        req = await self.extra(HttpResponse)  # type: HttpResponse
        return req.cookies


class AbstractWebsocketIO(PacketIO[Union[str, bytes]]):
    @abstractmethod
    async def receive(self) -> Union[str, bytes]:
        raise NotImplementedError

    @overload
    @abstractmethod
    async def send(self, data: bytes):
        ...

    @overload
    @abstractmethod
    async def send(self, data: str):
        ...

    @overload
    @abstractmethod
    async def send(self, data: Any):
        ...

    @abstractmethod
    async def send(self, data: ...):
        raise NotImplementedError

    @abstractmethod
    async def extra(self, signature: Any):
        raise NotImplementedError

    async def accept(self):
        await self.extra(websocket.accept)

    async def close(self):
        if not self.closed:
            await self.extra(websocket.close)

    async def packets(self):
        try:
            while not self.closed:
                yield await self.receive()
        except:
            pass


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
    class endpoint(
        TransportSignature[
            Callable[
                [AbstractServerRequestIO],
                Coroutine[None, None, T_HttpResponse],
            ]
        ]
    ):
        path: str
        method: List[Literal["GET", "POST", "PUT", "DELETE"]] = field(default_factory=lambda: ["GET"])  # type: ignore


class websocket:
    accept = TransportSignature[None]()
    close = TransportSignature[None]()

    class event:
        connect = TransportSignature[Callable[[AbstractWebsocketIO], Coroutine[None, None, Any]]]()
        receive = TransportSignature[Callable[[AbstractWebsocketIO, Union[bytes, str]], Coroutine[None, None, Any]]]()
        close = TransportSignature[Callable[[AbstractWebsocketIO], Coroutine[None, None, Any]]]()

    @dataclass
    class endpoint(
        http.endpoint,
        TransportSignature[Callable[[AbstractWebsocketIO], None]],
    ):
        method: Final[str] = "WS"
