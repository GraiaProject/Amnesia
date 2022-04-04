import asyncio

from aiohttp import ClientSession

from graia.amnesia.manager import LaunchManager
from graia.amnesia.transport.common.aiohttp import (
    AiohttpClientInterface,
    AiohttpService,
)
from graia.amnesia.transport.common.http import HttpResponse

loop = asyncio.get_event_loop()
mgr = LaunchManager()
mgr.add_service(AiohttpService(ClientSession(loop=loop)))


async def main(_):
    i = mgr.get_interface(AiohttpClientInterface)
    ws = (await i.websocket("http://localhost:8000/ws")).io()
    while not ws.closed:
        print(await ws.receive())


mgr.new_launch_component("test", mainline=main)
mgr.launch_blocking(loop=loop)
