import asyncio
import weakref
from functools import partial
from typing import Optional, Type

from aiohttp import ClientResponse, ClientSession

from graia.amnesia.interface import ExportInterface
from graia.amnesia.launch import LaunchComponent
from graia.amnesia.service import Service
from graia.amnesia.transport.common.http import (
    HttpClientResponseInterface,
    HttpResponseExtra,
)
from graia.amnesia.transport.interface import TransportInterface
from graia.amnesia.transport.rider import TransportRider
from graia.amnesia.transport.signature import TransportSignature


class AiohttpClientTransportInterface(HttpClientResponseInterface):
    response: ClientResponse

    def __init__(self, response: ClientResponse) -> None:
        self.response = response

    async def receive(self) -> bytes:
        return await self.response.read()

    async def extra(self, signature):
        if signature is HttpResponseExtra:
            return HttpResponseExtra(
                self.response.status,
                dict(self.response.headers),
                {k: str(v) for k, v in self.response.cookies.items()},
            )


class AiohttpClientInterface(ExportInterface["AiohttpService"]):
    service: "AiohttpService"

    def __init__(self, service: "AiohttpService") -> None:
        self.service = service

    async def request(
        self,
        method: str,
        url: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        headers: Optional[dict] = None,
        cookies: Optional[dict] = None,
        timeout: Optional[float] = None,
    ) -> AiohttpClientTransportInterface:
        response = await self.service.session.request(
            method,
            url,
            params=params,
            data=data,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
        ).__aenter__()
        return AiohttpClientTransportInterface(response)


class AiohttpService(Service):
    session: ClientSession

    supported_interface_types = {AiohttpClientInterface}

    def __init__(self, session: Optional[ClientSession] = None) -> None:
        self.session = session or ClientSession()

    def get_interface(self, interface_type):
        if interface_type is AiohttpClientInterface:
            return AiohttpClientInterface(self)

    @property
    def launch_component(self) -> LaunchComponent:
        return LaunchComponent(
            "http.universal_client", set(), cleanup=lambda _: self.session.close()
        )
