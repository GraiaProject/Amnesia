from __future__ import annotations

import asyncio
import logging
import re
from ssl import VerifyFlags, VerifyMode
from typing import Any, TypedDict

from hypercorn.asyncio import serve
from hypercorn.config import Config
from hypercorn.logging import Logger
from hypercorn.typing import ResponseSummary, WWWScope
from launart import Launart, Service
from launart.status import Phase
from launart.utilles import any_completed
from loguru import logger

from . import asgitypes
from .common import empty_asgi_handler
from .middleware import DispatcherMiddleware


class HypercornOptions(TypedDict, total=False):
    insecure_bind: str | list[str]
    """default: []"""
    quic_bind: str | list[str]
    """default: []"""
    root_path: str
    """default: ''"""

    access_log_format: str
    """default: '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'"""
    accesslog: logging.Logger | str | None
    """default: None"""
    alpn_protocols: list[str]
    """default: ['h2', 'http/1.1']"""
    alt_svc_headers: list[str]
    """default: []"""
    backlog: int
    """default: 100"""
    ca_certs: str | None
    """default: None"""
    certfile: str | None
    """default: None"""
    ciphers: str
    """default: 'ECDHE+AESGCM'"""
    dogstatsd_tags: str
    """default: ''"""
    errorlog: logging.Logger | str | None
    """default: '-'"""
    graceful_timeout: float
    """default: 3.0"""
    read_timeout: int | None
    """default: None"""
    group: int | None
    """default: None"""
    h11_max_incomplete_size: int
    """default: 16 * 1024"""
    h11_pass_raw_headers: bool
    """default: False"""
    h2_max_concurrent_streams: int
    """default: 100"""
    h2_max_header_list_size: int
    """default: 2 ** 16"""
    h2_max_inbound_frame_size: int
    """default: 2 ** 14"""
    include_date_header: bool
    """default: True"""
    include_server_header: bool
    """default: True"""
    keep_alive_timeout: float
    """default: 5.0"""
    keep_alive_max_requests: int
    """default: 1000"""
    keyfile: str | None
    """default: None"""
    keyfile_password: str | None
    """default: None"""
    logger_class: type
    """default: hypercorn.logging.Logger"""
    logconfig: str | None
    """default: None"""
    logconfig_dict: dict | None
    """default: None"""
    loglevel: str
    """default: 'INFO'"""
    max_app_queue_size: int
    """default: 10"""
    max_requests: int | None
    """default: None"""
    max_requests_jitter: int
    """default: 0"""
    pid_path: str | None
    """default: None"""
    server_names: list[str]
    """default: []"""
    shutdown_timeout: float
    """default: 60.0"""
    ssl_handshake_timeout: float
    """default: 60.0"""
    startup_timeout: float
    """default: 60.0"""
    statsd_host: str | None
    """default: None"""
    statsd_prefix: str
    """default: ''"""
    umask: int | None
    """default: None"""
    use_reloader: bool
    """default: False"""
    user: int | None
    """default: None"""
    verify_flags: VerifyFlags | None
    """default: None"""
    verify_mode: VerifyMode | None
    """default: None"""
    websocket_max_message_size: int
    """default: 16 * 1024 * 1024"""
    websocket_ping_interval: float | None
    """default: None"""
    worker_class: str
    """default: 'asyncio'"""
    wsgi_max_body_size: int
    """default: 16 * 1024 * 1024"""


class LoguruLogger(Logger):
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.access_template = re.sub(r"%\(([^)]+)\)s", r"{\1}", self.access_log_format)
        self.access_template = self.access_template.replace("{t} ", "")

    async def access(self, request: WWWScope, response: ResponseSummary, request_time: float) -> None:
        if self.access_logger is not None:
            logger.info(self.access_template.format(**self.atoms(request, response, request_time)))

    async def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        logger.critical(message, *args, **kwargs)

    async def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        logger.error(message, *args, **kwargs)

    async def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        logger.warning(message, *args, **kwargs)

    async def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        logger.info(message, *args, **kwargs)

    async def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        logger.debug(message, *args, **kwargs)

    async def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        logger.exception(message, *args, **kwargs)

    async def log(self, level: int, message: str, *args: Any, **kwargs: Any) -> None:
        logger.log(level, message, *args, **kwargs)


class HypercornASGIService(Service):
    id = "asgi.service/hypercorn"

    middleware: DispatcherMiddleware
    host: str
    port: int

    def __init__(
        self,
        host: str,
        port: int,
        mounts: dict[str, asgitypes.ASGI3Application] | None = None,
        options: HypercornOptions | None = None,
        patch_logger: bool = True,
    ):
        self.host = host
        self.port = port
        self.middleware = DispatcherMiddleware(mounts or {"\0\0\0": empty_asgi_handler})
        self.options = options or {}
        if patch_logger:
            self.options["logger_class"] = LoguruLogger  # type: ignore
        super().__init__()

    @property
    def required(self):
        return set()

    @property
    def stages(self) -> set[Phase]:
        return {"preparing", "blocking", "cleanup"}

    async def launch(self, manager: Launart) -> None:
        async with self.stage("preparing"):
            shutdown_trigger = asyncio.Event()
            serve_task = asyncio.create_task(
                serve(
                    self.middleware,  # type: ignore
                    Config.from_mapping(bind=f"{self.host}:{self.port}", **self.options),
                    shutdown_trigger=shutdown_trigger.wait,
                )
            )

        async with self.stage("blocking"):
            await any_completed(serve_task, manager.status.wait_for_sigexit())

        async with self.stage("cleanup"):
            logger.warning("trying to shutdown hypercorn server...")
            shutdown_trigger.set()
            try:
                await asyncio.wait_for(serve_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("timeout, force exit hypercorn server...")
