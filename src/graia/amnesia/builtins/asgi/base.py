import asyncio
from abc import ABCMeta, abstractmethod
from enum import StrEnum
from typing import Generic, TypeVar, Literal, TypeAlias

from launart import Service
from launart.status import Phase

from . import asgitypes
from .common import empty_asgi_handler
from .middleware import DispatcherMiddleware


TOption = TypeVar("TOption")
Loops: TypeAlias = Literal["auto", "asyncio", "uvloop", "winloop"]


class ASGIService(Service, Generic[TOption], metaclass=ABCMeta):
    id = "asgi.service"

    middleware: DispatcherMiddleware
    host: str
    port: int
    options: TOption

    def __init__(
        self,
        host: str,
        port: int,
        mounts: dict[str, asgitypes.ASGI3Application] | None = None,
        options: TOption | None = None,
        patch_logger: bool = True,
        loop: Loops = "auto",
    ):
        self.host = host
        self.port = port
        self.patch_logger = patch_logger
        self.middleware = DispatcherMiddleware(mounts or {"\0\0\0": empty_asgi_handler})
        self.options: TOption = options or self._options_default()
        self.loop = loop
        super().__init__()
        self.install_loop()

    @property
    def required(self):
        return set()

    @property
    def stages(self) -> set[Phase]:
        return {"preparing", "blocking", "cleanup"}

    @staticmethod
    @abstractmethod
    def _options_default() -> TOption:
        raise NotImplementedError("base asgi service does not implement options default method")

    def install_loop(self):
        if self.loop == "asyncio":
            return
        try:
            import uvloop  # type: ignore

            if self.loop in ("auto", "uvloop"):
                asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())  # type: ignore
        except ImportError:
            if self.loop == "uvloop":
                raise RuntimeError("uvloop is not installed, cannot use uvloop as event loop policy")

        try:
            import winloop  # type: ignore

            if self.loop in ("auto", "winloop"):
                asyncio.set_event_loop_policy(winloop.EventLoopPolicy())  # type: ignore
        except ImportError:
            if self.loop == "winloop":
                raise RuntimeError("winloop is not installed, cannot use winloop as event loop policy")
