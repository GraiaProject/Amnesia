import asyncio
from re import A
from typing import (
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    TypedDict,
    TypeVar,
    Union,
    cast,
    overload,
)

from .abc import AbstractStatus

T = TypeVar("T", bound=AbstractStatus)
TWaiterFtr = asyncio.Future  # [Tuple[Optional[AbstractStatus], Optional[AbstractStatus]]]  # type: ignore


class StatusManager:
    components: List[AbstractStatus]

    _id_component_cache: Dict[str, AbstractStatus]
    _waiters: Dict[str, TWaiterFtr]

    def __init__(self):
        self.components = []
        self._id_component_cache = {}
        self.frozens = set()
        self._waiters = {}

    def _cache(self):
        self._id_component_cache = {i.id: i for i in self.components}

    def _dispose_waiter(self, target: Union[str, AbstractStatus]):
        self.exists(target, error=True)
        target_id = target.id if isinstance(target, AbstractStatus) else target
        if target_id in self._waiters:
            ftr = self._waiters[target_id]
            if not ftr.cancelled() or not ftr.done():
                self._waiters[target_id].cancel()
            del self._waiters[target_id]

    def notify_update_callback(
        self,
        sid: str,
        past: Optional[AbstractStatus] = None,
        current: Optional[AbstractStatus] = None,
    ):
        asyncio.create_task(asyncio.wait([i.on_required_updated(sid, past, current) for i in self._get_required(sid)]))

    def _get_required(self, target: Union[AbstractStatus, str]):
        if isinstance(target, AbstractStatus):
            target = target.id
        return [i for i in self.components if target in i.required]

    def notify_update(self, status: AbstractStatus, past: Optional[AbstractStatus] = None):
        self.exists(status, error=True)
        ftr = self._waiters.get(status.id)
        if ftr is not None:
            if not ftr.done():
                ftr.set_result((past, status))
            del self._waiters[status.id]
        self.notify_update_callback(status.id, past, status)

    def notify_global(self, past: Optional[AbstractStatus], current: Optional[AbstractStatus]):
        ftr = self._waiters.get("#")
        if ftr is not None:
            if not ftr.done():
                ftr.set_result((past, current))
            del self._waiters["#"]

    def exists(self, target: Union[AbstractStatus, str], *, error: bool = False):
        if isinstance(target, str):
            result = target in self._id_component_cache
            if not result and error:
                raise ValueError(f"{target} is not a existed target")
            return result
        elif isinstance(target, AbstractStatus):
            result = target.id in self._id_component_cache
            if not result and error:
                raise ValueError(f"{target} is not a existed target")
            return result
        else:
            raise TypeError(f"{target} is not a valid target")

    def mount(self, component: AbstractStatus):
        self.components.append(component)
        self._cache()
        component._set_manager(self)
        self.notify_global(None, component)
        self._ensure_waiter(component)  # Not Sure
        return component.id

    @overload
    def unmount(self, target: AbstractStatus):
        ...

    @overload
    def unmount(self, target: str):
        ...

    def unmount(self, target: Union[AbstractStatus, str]):
        self.exists(target, error=True)

        if isinstance(target, str):
            target = cast(AbstractStatus, self.get(target))

        self.components.remove(target)
        self._cache()
        self.notify_global(target, None)

    @overload
    def get(self, id: str) -> Optional[AbstractStatus]:
        ...

    @overload
    def get(self, status_type: Type[T]) -> List[T]:
        ...

    @overload
    def get(self, status_type: Type[T], map: Literal[True] = True) -> Dict[str, T]:
        ...

    def get(self, target: Union[str, Type[T]], map: bool = False):  # type: ignore
        if isinstance(target, str):
            return self._id_component_cache.get(target)
        if map:
            return {k: v for k, v in self._id_component_cache.items() if isinstance(v, target)}
        else:
            return [v for v in self._id_component_cache.values() if isinstance(v, target)]

    def _get_waiter(self, target: Union[str, AbstractStatus]) -> Optional[TWaiterFtr]:
        self.exists(target, error=True)
        return self._waiters.get(target.id if isinstance(target, AbstractStatus) else target, None)  # type: ignore

    def _ensure_waiter(self, target: Union[str, AbstractStatus]):
        self.exists(target, error=True)
        if isinstance(target, str):
            target = cast(AbstractStatus, self.get(target))
        if target.id in self._waiters:
            return self._waiters[target.id]
        ftr = asyncio.Future()
        self._waiters[target.id] = ftr
        return ftr

    def _exists_waiter(self, target: Union[str, AbstractStatus]) -> bool:
        self.exists(target, error=True)
        if isinstance(target, str):
            target = cast(AbstractStatus, self.get(target))
        return target.id in self._waiters
