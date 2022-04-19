import asyncio
import logging

from loguru import logger
from uvicorn import Config, Server

from graia.amnesia.builtins.common import ASGIHandlerProvider
from graia.amnesia.launch.component import LaunchComponent
from graia.amnesia.launch.manager import LaunchManager
from graia.amnesia.launch.service import Service
from graia.amnesia.log import LoguruHandler


class WithoutSigHandlerServer(Server):
    def install_signal_handlers(self) -> None:
        return


class UvicornService(Service):
    supported_interface_types = set()
    supported_description_types = set()

    server: Server
    host: str
    port: int

    server_sigexit: asyncio.Event

    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        self.host = host
        self.port = port
        self.server_sigexit = asyncio.Event()

    def get_interface(self, interface_type):
        pass

    async def launch_prepare(self, manager: LaunchManager):
        asgi_handler = manager.get_interface(ASGIHandlerProvider).get_asgi_handler()
        self.server = WithoutSigHandlerServer(Config(asgi_handler, host=self.host, port=self.port))
        # TODO: 使用户拥有更多的对 Config 的配置能力.
        PATCHES = "uvicorn.error", "uvicorn.asgi", "uvicorn.access", ""
        level = logging.getLevelName(20)  # default level for uvicorn
        logging.basicConfig(handlers=[LoguruHandler()], level=level)
        for name in PATCHES:
            target = logging.getLogger(name)
            target.handlers = [LoguruHandler(level=level)]
            target.propagate = False

    async def launch_mainline(self, manager: LaunchManager):
        await self.server.serve()
        self.server_sigexit.set()

    async def launch_cleanup(self, _):
        logger.warning("try to shutdown uvicorn server...")
        self.server.should_exit = True
        await asyncio.wait([self.server_sigexit.wait(), asyncio.sleep(10)], return_when=asyncio.FIRST_COMPLETED)
        if not self.server_sigexit.is_set():
            logger.warning("timeout, force exit uvicorn server...")
            self.server.force_exit = True

    @property
    def launch_component(self) -> LaunchComponent:
        return LaunchComponent(
            "http.asgi_runner",
            {"http.universal_server"},
            self.launch_mainline,
            self.launch_prepare,
            self.launch_cleanup,
        )
