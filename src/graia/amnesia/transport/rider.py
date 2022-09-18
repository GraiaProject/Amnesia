from __future__ import annotations

import asyncio
from abc import ABCMeta, abstractmethod
from collections.abc import MutableMapping
from itertools import chain
from typing import Generic, TypeVar

from loguru import logger

from graia.amnesia.transport import Transport

K = TypeVar("K")
V = TypeVar("V")


class TransportRider(Generic[K, V], metaclass=ABCMeta):
    connections: MutableMapping[K, V]
    transports: list[Transport]

    @abstractmethod
    def io(self, id: K | None = None):
        raise NotImplementedError

    @abstractmethod
    def use(self, transport: Transport):
        raise NotImplementedError

    async def trigger_callbacks(self, event, *args, **kwargs):
        result = await asyncio.gather(
            *(c(*args, **kwargs) for c in chain.from_iterable(t.get_callbacks(event) for t in self.transports)),
            return_exceptions=True,
        )
        base_excs: set[BaseException] = set(filter(lambda e: isinstance(e, BaseException), result))
        excs: set[Exception] = set(filter(lambda e: isinstance(e, Exception), result))
        for exc in excs:
            logger.opt(exception=exc).error(exc)
        if base_excs := base_excs - excs:
            raise base_excs.pop()
