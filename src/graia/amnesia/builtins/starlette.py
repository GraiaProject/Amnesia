from typing import Optional

from starlette.applications import Starlette

from graia.amnesia.builtins.common import ASGIHandlerProvider
from graia.amnesia.launch import LaunchComponent
from graia.amnesia.service import Service

# 这里为简化版, 完整版是在 avilla.io 那边


class StarletteServer(ASGIHandlerProvider):
    starlette: Starlette
    service: "StarletteService"

    def __init__(self, service: "StarletteService", starlette: Starlette):
        self.service = service
        self.starlette = starlette

        super().__init__()

    def get_asgi_handler(self):
        return self.starlette


class StarletteService(Service):
    supported_interface_types = {ASGIHandlerProvider}

    starlette: Starlette

    def __init__(self, starlette: Optional[Starlette] = None) -> None:
        self.starlette = starlette or Starlette()
        super().__init__()

    def get_interface(self, interface_type):
        if issubclass(interface_type, (ASGIHandlerProvider)):
            return StarletteServer(self, self.starlette)
        raise ValueError(f"unsupported interface type {interface_type}")

    @property
    def launch_component(self) -> LaunchComponent:
        return LaunchComponent("http.universal_server", set())
