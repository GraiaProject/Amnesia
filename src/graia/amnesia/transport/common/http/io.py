from abc import abstractmethod
from typing import Any, Dict

from graia.amnesia.transport.common.http.extra import HttpRequest, HttpResponse
from graia.amnesia.transport.interface import ReadonlyIO


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
