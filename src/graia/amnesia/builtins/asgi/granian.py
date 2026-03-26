import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from granian.constants import HTTPModes, Interfaces, SSLProtocols, TaskImpl
from granian.http import HTTP1Settings, HTTP2Settings
from granian.log import LogLevels, log_levels_map
from granian.server.embed import Server
from launart import Launart
from launart.status import Phase
from launart.utilles import any_completed
from loguru import logger

from ..utils import LoguruHandler
from .base import ASGIService


@dataclass
class GranianOptions:
    uds: Path | None = None
    blocking_threads: int | None = None
    blocking_threads_idle_timeout: int = 30
    runtime_threads: int = 1
    runtime_blocking_threads: int | None = None
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


class GranianASGIService(ASGIService[GranianOptions]):
    id = "asgi.service/granian"
    server: Server

    @staticmethod
    def _options_default() -> GranianOptions:
        return GranianOptions()

    async def launch(self, manager: Launart) -> None:
        async with self.stage("preparing"):
            if self.patch_logger:
                self.options.log_access_format = (
                    self.options.log_access_format
                    or '%(addr)s - "%(method)s %(path)s %(protocol)s" %(status)d %(dt_ms).3f'
                )
            options = vars(self.options)
            options.pop("loop")
            self.server = Server(self.middleware, self.host, self.port, interface=Interfaces.ASGI, **options)
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
