import asyncio

from aiohttp import ClientSession

from graia.amnesia.manager import LaunchManager
from graia.amnesia.transport.common.aiohttp import (
    AiohttpClientInterface,
    AiohttpService,
)
from graia.amnesia.transport.common.http import HttpResponseExtra

loop = asyncio.get_event_loop()
mgr = LaunchManager()
mgr.add_service(AiohttpService(ClientSession(loop=loop)))


async def main(_):
    i = mgr.get_interface(AiohttpClientInterface)
    resp = await i.request("GET", "http://example.com")
    print(await resp.receive())
    print(await resp.extra(HttpResponseExtra))


mgr.new_launch_component("test", mainline=main)
mgr.launch_blocking(loop=loop)
