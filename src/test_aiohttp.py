import asyncio

from aiohttp import ClientSession
from loguru import logger

from graia.amnesia.manager import LaunchManager
from graia.amnesia.transport import Transport
from graia.amnesia.transport.common.aiohttp import (
    AiohttpClientInterface,
    AiohttpService,
)
from graia.amnesia.transport.common.http import (
    AbstractWebsocketIO,
    HttpResponse,
    websocket,
)
from graia.amnesia.transport.utilles import CallbackRegistrar, HandlerRegistrar

loop = asyncio.get_event_loop()
mgr = LaunchManager()
mgr.add_service(AiohttpService(ClientSession(loop=loop)))

h = CallbackRegistrar()


@h.apply
class TestWebsocket(Transport):
    @h.signature(websocket.event.connect)
    async def connected(self, io: AbstractWebsocketIO):
        logger.success("websocket connected!")
        await io.send(b"hello!")

    @h.signature(websocket.event.receive)
    async def received(self, io: AbstractWebsocketIO, data: bytes):
        logger.success(f"websocket received: {data}")
        await io.send(b"bye!")
        # await io.close()

    @h.signature(websocket.event.close)
    async def closed(self, io: AbstractWebsocketIO):
        logger.success("websocket closed!")


async def main(_):
    i = mgr.get_interface(AiohttpClientInterface)
    ws = await i.websocket("http://localhost:8000/ws")
    await ws.use(TestWebsocket())


mgr.new_launch_component("test", mainline=main)
mgr.launch_blocking(loop=loop)
