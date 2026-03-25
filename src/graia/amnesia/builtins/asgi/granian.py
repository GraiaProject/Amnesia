import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from granian.constants import Interfaces, SSLProtocols, TaskImpl, HTTPModes
from granian.http import HTTP2Settings, HTTP1Settings
from granian.server.embed import Server
from granian.log import LogLevels, log_levels_map
from launart import Launart, Service
from launart.status import Phase
from launart.utilles import any_completed
from loguru import logger

from ..utils import LoguruHandler
from . import asgitypes

from .common import empty_asgi_handler
from .middleware import DispatcherMiddleware


@dataclass
class GranianOptions:
    uds: Path | None = None
    blocking_threads: int | None = None
    blocking_threads_idle_timeout: int = 30
    runtime_threads: int = 1
    runtime_blocking_threads: int | None = None
    # loop: Loops = Loops.auto
    task_impl: TaskImpl = TaskImpl.asyncio
    http: HTTPModes = HTTPModes.auto
    websockets: bool = True
    backlog: int = 128
    backpressure: int | None = None
    http1_settings: HTTP1Settings | None = None
    http2_settings: HTTP2Settings | None = None
    log_enabled: bool = True
    log_level: LogLevels = LogLevels.info
    log_dictconfig: dict[str, Any] | None = None
    log_access: bool = False
    log_access_format: str | None = None
    ssl_cert: Path | None = None
    ssl_key: Path | None = None
    ssl_key_password: str | None = None
    ssl_protocol_min: SSLProtocols = SSLProtocols.tls13
    ssl_ca: Path | None = None
    ssl_crl: list[Path] | None = None
    ssl_client_verify: bool = False
    url_path_prefix: str | None = None
    factory: bool = False
    static_path_route: Sequence[str] | None = None
    static_path_mount: Sequence[Path] | None = None
    static_path_dir_to_file: str | None = None
    static_path_expires: int = 86400


class GranianASGIService(Service):
    id = "asgi.service/granian"

    middleware: DispatcherMiddleware
    host: str
    port: int

    def __init__(
        self,
        host: str,
        port: int,
        mounts: dict[str, asgitypes.ASGI3Application] | None = None,
        options: GranianOptions | None = None,
        patch_logger: bool = True,
    ):
        self.host = host
        self.port = port
        self.patch_logger = patch_logger
        self.middleware = DispatcherMiddleware(mounts or {"\0\0\0": empty_asgi_handler})
        self.options: GranianOptions = options or GranianOptions()
        super().__init__()

    @property
    def required(self):
        return set()

    @property
    def stages(self) -> set[Phase]:
        return {"preparing", "blocking", "cleanup"}

    async def launch(self, manager: Launart) -> None:
        async with self.stage("preparing"):
            if self.patch_logger:
                self.options.log_access_format = self.options.log_access_format or '%(addr)s - "%(method)s %(path)s %(protocol)s" %(status)d %(dt_ms).3f'
            self.server = Server(self.middleware, self.host, self.port, interface=Interfaces.ASGI, **vars(self.options))
            if self.patch_logger:
                self._patch_logger()
            serve_task = asyncio.create_task(self.server.serve())

        async with self.stage("blocking"):
            await any_completed(serve_task, manager.status.wait_for_sigexit())

        async with self.stage("cleanup"):
            logger.warning("try to shutdown granian server...")
            self.server.stop()
            await any_completed(serve_task, asyncio.sleep(5))
            if not serve_task.done():
                logger.warning("timeout, force exit granian server...")
                await self.server.shutdown(1)

    def _patch_logger(self) -> None:
        log_level = log_levels_map[self.options.log_level]
        PATCHES = ["_granian", "_granian.serve"]
        if self.options.log_access:
            PATCHES.append("granian.access")
        for name in PATCHES:
            target = logging.getLogger(name)
            target.handlers = [LoguruHandler()]
            target.propagate = False
            target.setLevel(log_level)
