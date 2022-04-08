import asyncio
from typing import Dict, List, Union, overload

from graia.amnesia.status.abc import AbstractStatus


class StatusManager:
    components: List[AbstractStatus]

    _id_component_cache: Dict[str, AbstractStatus]
    _waiters: Dict[str, List[asyncio.Future]]

    def __init__(self):
        self.components = []
        self._id_component_cache = {}

    def _cache(self):
        self._id_component_cache = {i.id: i for i in self.components}

    def mount(self, component: AbstractStatus):
        self.components.append(component)
        self._cache()
        component._set_manager(self)
        return component.id

    @overload
    def unmount(self, target: AbstractStatus):
        ...

    @overload
    def unmount(self, target: str):
        ...

    def unmount(self, target: Union[AbstractStatus, str]):
        pass
