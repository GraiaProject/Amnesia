import asyncio
from datetime import timedelta
from heapq import heappop, heappush
from time import time
from typing import Any, Dict, List, Optional, Tuple, Type

from graia.amnesia.interface import ExportInterface
from graia.amnesia.launch import LaunchComponent
from graia.amnesia.manager import LaunchManager
from graia.amnesia.service import Service


class Memcache(ExportInterface):
    cache: Dict[str, Tuple[Optional[float], Any]]
    expire: List[Tuple[float, str]]

    def __init__(
        self,
        cache: Dict[str, Tuple[Optional[float], Any]],
        expire: List[Tuple[float, str]],
    ):
        self.cache = cache
        self.expire = expire

    async def get(self, key: str, default: Optional[Any] = None) -> Any:
        value = self.cache.get(key)
        if value:
            if value[0] is None or value[0] >= time():
                return value[1]
            else:
                del self.cache[key]
        return default

    async def set(self, key: str, value: Any, expire: Optional[timedelta] = None) -> None:
        if expire is None:
            self.cache[key] = (None, value)
            return

        expire_time = time() + expire.total_seconds()
        self.cache[key] = (expire_time, value)
        heappush(self.expire, (expire_time, value))

    async def delete(self, key: str, strict: bool = False) -> None:
        if key not in self.cache:
            if strict:
                raise KeyError(key)
        else:
            del self.cache[key]

    async def clear(self) -> None:
        self.cache.clear()
        self.expire.clear()

    async def has(self, key: str) -> bool:
        return key in self.cache

    async def keys(self) -> List[str]:
        return list(self.cache.keys())


class MemcacheService(Service):
    supported_interface_types = {Memcache}

    interval: float
    cache: Dict[str, Tuple[Optional[float], Any]]
    expire: List[Tuple[float, str]]

    def __init__(
        self,
        interval: float = 0.1,
        cache: Optional[Dict[str, Tuple[Optional[float], Any]]] = None,
        expire: Optional[List[Tuple[float, str]]] = None,
    ):
        self.interval = interval
        self.cache = cache if cache else {}
        self.expire = expire if expire else []
        super().__init__()

    def get_interface(self, interface_type: Type[Memcache]) -> Memcache:
        if issubclass(interface_type, (Memcache)):
            return Memcache(self.cache, self.expire)
        raise ValueError(f"unsupported interface type {interface_type}")

    def get_status(self, _):
        raise NotImplementedError

    @property
    def launch_component(self) -> LaunchComponent:
        return LaunchComponent("cache.client", set(), mainline=self.launch_mainline)

    async def launch_mainline(self, manager: LaunchManager) -> None:
        while not manager.sigexit.is_set():
            if self.expire:
                expire_time, key = self.expire[0]
                while expire_time <= time():
                    self.cache.pop(key, None)
                    heappop(self.expire)
                    expire_time, key = self.expire[0]
            await asyncio.sleep(self.interval)
