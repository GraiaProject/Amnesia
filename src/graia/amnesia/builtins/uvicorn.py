import asyncio

from uvicorn import Config, Server

from graia.amnesia.builtins.common import ASGIHandlerProvider
from graia.amnesia.launch import LaunchComponent
from graia.amnesia.manager import LaunchManager
from graia.amnesia.service import Service


class UvicornService(Service):
    supported_interface_types = set()
    supported_description_types = set()

    server: Server
    host: str
    port: int

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def get_interface(self, interface_type):
        pass

    def get_status(self, entity):
        raise NotImplementedError

    def set_status(self, entity, available: bool, description: str):
        raise NotImplementedError

    def set_current_status(self, available: bool, description: str):
        raise NotImplementedError

    async def launch_prepare(self, manager: LaunchManager):
        asgi_handler = manager.get_interface(ASGIHandlerProvider).get_asgi_handler()
        self.server = Server(Config(asgi_handler, host=self.host, port=self.port))
        # TODO: 使用户拥有更多的对 Config 的配置能力.

    async def launch_mainline(self, manager: "LaunchManager"):
        await self.server.serve()
        manager.sigexit.set()
        if manager.maintask:
            manager.maintask.cancel()
        for task in asyncio.all_tasks():
            if task.get_name() == "amnesia-launch":
                task.cancel()

    @property
    def launch_component(self) -> LaunchComponent:
        return LaunchComponent(
            "http.asgi_runner",
            {"http.universal_server"},
            self.launch_mainline,
            self.launch_prepare,
        )
