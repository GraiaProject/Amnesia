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
        req: HttpRequest = await self.extra(HttpRequest)
        return req.headers

    async def cookies(self) -> Dict[str, str]:
        req: HttpRequest = await self.extra(HttpRequest)
        return req.cookies


class AbstactClientRequestIO(ReadonlyIO[bytes]):
    @abstractmethod
    async def read(self) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def extra(self, signature: Any):
        raise NotImplementedError

    async def headers(self) -> Dict[str, str]:
        req: HttpResponse = await self.extra(HttpResponse)
        return req.headers

    async def cookies(self) -> Dict[str, str]:
        req: HttpResponse = await self.extra(HttpResponse)
        return req.cookies
