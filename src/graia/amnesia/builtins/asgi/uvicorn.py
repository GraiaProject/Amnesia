import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from typing import IO, Any, Literal, TypedDict

from launart import Launart, Service
from launart.status import Phase
from launart.utilles import any_completed
from loguru import logger
from uvicorn import Config, Server
from uvicorn.config import LOG_LEVELS, LOOP_FACTORIES, HTTPProtocolType, LifespanType, WSProtocolType

from ..utils import LoguruHandler
from . import asgitypes
from .common import empty_asgi_handler
from .middleware import DispatcherMiddleware

LOOP_FACTORIES["winloop"] = "graia.amnesia.builtins.asgi.winloop:winloop_loop_factory"


class WithoutSigHandlerServer(Server):
    def install_signal_handlers(self) -> None:
        pass


class UvicornOptions(TypedDict, total=False):
    uds: str | None
    """default: None"""
    fd: int | None
    """default: None"""
    loop: Literal["none", "auto", "asyncio", "uvloop", "winloop"]
    """default: 'auto'"""
    http: type[asyncio.Protocol] | HTTPProtocolType
    """default: 'auto'"""
    ws: type[asyncio.Protocol] | WSProtocolType
    """default: 'auto'"""
    ws_max_size: int
    """default: 16 * 1024 * 1024"""
    ws_max_queue: int
    """default: 32"""
    ws_ping_interval: float | None
    """default: 20.0"""
    ws_ping_timeout: float | None
    """default: 20.0"""
    ws_per_message_deflate: bool
    """default: True"""
    lifespan: LifespanType
    """default: 'auto'"""
    env_file: str | os.PathLike[str] | None
    """default: None"""
    log_config: dict[str, Any] | str | IO[Any] | None
    """default: LOGGING_CONFIG"""
    log_level: str | int | None
    """default: None"""
    access_log: bool
    """default: True"""
    use_colors: bool | None
    """default: None"""
    # interface: InterfaceType
    # """default: 'auto'"""
    reload: bool
    """default: False"""
    reload_dirs: list[str] | str | None
    """default: None"""
    reload_delay: float
    """default: 0.25"""
    reload_includes: list[str] | str | None
    """default: None"""
    reload_excludes: list[str] | str | None
    """default: None"""
    workers: int | None
    """default: None"""
    proxy_headers: bool
    """default: True"""
    server_header: bool
    """default: True"""
    date_header: bool
    """default: True"""
    forwarded_allow_ips: list[str] | str | None
    """default: None"""
    root_path: str
    """default: ''"""
    limit_concurrency: int | None
    """default: None"""
    limit_max_requests: int | None
    """default: None"""
    backlog: int
    """default: 2048"""
    timeout_keep_alive: int
    """default: 5"""
    timeout_notify: int
    """default: 30"""
    timeout_graceful_shutdown: int | None
    """default: None"""
    callback_notify: Callable[..., Awaitable[None]] | None
    """default: None"""
    ssl_keyfile: str | os.PathLike[str] | None
    """default: None"""
    ssl_certfile: str | os.PathLike[str] | None
    """default: None"""
    ssl_keyfile_password: str | None
    """default: None"""
    ssl_version: int
    """default: ssl.PROTOCOL_TLS"""
    ssl_cert_reqs: int
    """default: ssl.CERT_NONE"""
    ssl_ca_certs: str | None
    """default: None"""
    ssl_ciphers: str
    """default: 'TLSv1'"""
    headers: list[tuple[str, str]] | None
    """default: None"""
    h11_max_incomplete_event_size: int | None
    """default: None"""


class UvicornASGIService(Service):
    id = "asgi.service/uvicorn"

    middleware: DispatcherMiddleware
    host: str
    port: int

    def __init__(
        self,
        host: str,
        port: int,
        mounts: dict[str, asgitypes.ASGI3Application] | None = None,
        options: UvicornOptions | None = None,
        patch_logger: bool = True,
    ):
        self.host = host
        self.port = port
        self.patch_logger = patch_logger
        self.middleware = DispatcherMiddleware(mounts or {"\0\0\0": empty_asgi_handler})
        self.options: UvicornOptions = options or {}

        if self.options.get("loop", "auto") == "auto":
            try:
                import uvloop  # type: ignore

                self.options["loop"] = "uvloop"
            except ImportError:
                pass

            try:
                import winloop

                self.options["loop"] = "winloop"
            except ImportError:
                pass

            self.options["loop"] = "asyncio"

        super().__init__()

    @property
    def required(self):
        return set()

    @property
    def stages(self) -> set[Phase]:
        return {"preparing", "blocking", "cleanup"}

    async def launch(self, manager: Launart) -> None:
        async with self.stage("preparing"):
            self.server = WithoutSigHandlerServer(
                Config(self.middleware, host=self.host, port=self.port, factory=False, **self.options)
            )
            if self.patch_logger:
                self._patch_logger()
            serve_task = asyncio.create_task(self.server.serve())

        async with self.stage("blocking"):
            await any_completed(serve_task, manager.status.wait_for_sigexit())

        async with self.stage("cleanup"):
            logger.warning("try to shutdown uvicorn server...")
            self.server.should_exit = True
            await any_completed(serve_task, asyncio.sleep(5))
            if not serve_task.done():
                logger.warning("timeout, force exit uvicorn server...")

    def _patch_logger(self) -> None:
        log_level = 20
        if "log_level" in self.options and (_log_level := self.options["log_level"]) is not None:
            if isinstance(_log_level, str):
                log_level = LOG_LEVELS[_log_level]
            else:
                log_level = _log_level
        PATCHES = ["uvicorn.error", "uvicorn.asgi", "uvicorn"]
        if "access_log" not in self.options or self.options.get("access_log", True):
            PATCHES.append("uvicorn.access")
        for name in PATCHES:
            target = logging.getLogger(name)
            target.handlers = [LoguruHandler()]
            target.propagate = False
            target.setLevel(log_level)
