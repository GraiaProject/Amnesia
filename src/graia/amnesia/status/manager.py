import asyncio
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

from graia.amnesia.status.abc import AbstractStatus

T = TypeVar("T", bound=AbstractStatus)
TWaiterType = Literal["statupdate", "statmount", "statunmount", "statfreeze"]
TWaiterFtr = asyncio.Future[Tuple[Optional[AbstractStatus], Optional[AbstractStatus]]]


class _StatusManagerWaiters(TypedDict):
    # 多个类型的 Waiter... 也就是用途
    statupdate: Dict[Union[Literal["#"], str], List[TWaiterFtr]]
    statmount: Dict[Union[Literal["#"], str], List[TWaiterFtr]]
    statunmount: Dict[Union[Literal["#"], str], List[TWaiterFtr]]
    statfreeze: Dict[Union[Literal["#"], str], List[TWaiterFtr]]


class StatusManager:
    components: List[AbstractStatus]
    frozens: Set[str]

    _id_component_cache: Dict[str, AbstractStatus]
    _waiters: _StatusManagerWaiters

    def __init__(self):
        self.components = []
        self._id_component_cache = {}
        self.frozens = set()
        self._waiters = {"statupdate": {}, "statmount": {}, "statunmount": {}, "statfreeze": {}}

    def _cache(self):
        self._id_component_cache = {i.id: i for i in self.components}

    def _trig_waiters(self, waittype: TWaiterType, id: str, past: Optional[T], current: Optional[T]):
        waiters = self._waiters[waittype].get(id, [])
        for waiter in waiters:
            waiter.set_result((past, current))
        self._waiters[waittype].pop(id, None)

    def _ensure_waiters_from_required(self, id: str):
        if not self.exists(id):
            raise ValueError(f"{id} is not a existed target")

        # TODO: 等候 block 的算法实现...
        # 全部用 Future: 因为我希望 update 可以同步进行, 因为是 in-process 状态, 所以不需要异步.
        # 不过, 你还是得支持 async 才行.

    def exists(self, target: Union[AbstractStatus, str]):
        if isinstance(target, str):
            return target in self._id_component_cache
        elif isinstance(target, AbstractStatus):
            return target.id in self._id_component_cache
        else:
            raise TypeError(f"{target} is not a valid target")

    def mount(self, component: AbstractStatus):
        self.components.append(component)
        self._cache()
        component._set_manager(self)
        self._trig_waiters("statmount", "#", None, component)
        return component.id

    @overload
    def unmount(self, target: AbstractStatus):
        ...

    @overload
    def unmount(self, target: str):
        ...

    def unmount(self, target: Union[AbstractStatus, str]):
        if not self.exists(target):
            raise ValueError(f"{target} is not a existed target")

        if isinstance(target, str):
            target = cast(AbstractStatus, self.get(target))

        self.components.remove(target)
        self._cache()
        self._trig_waiters("statunmount", target.id, target, None)

    @overload
    def freeze(self, target: AbstractStatus):
        ...

    @overload
    def freeze(self, target: str):
        ...

    def freeze(self, target: Union[AbstractStatus, str]):
        if not self.exists(target):
            raise ValueError(f"{target} is not a existed target")
        if isinstance(target, str):
            self.frozens.add(target)
        elif isinstance(target, AbstractStatus):
            self.frozens.add(target.id)
        else:
            raise TypeError(f"{target} is not a valid target")

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
