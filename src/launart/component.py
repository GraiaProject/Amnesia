from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, List, Optional, Set

from graia.amnesia.status.standalone import AbstractStandaloneStatus

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

if TYPE_CHECKING:
    from launart.manager import Launart

U_Stage = Literal["prepare", "blocking", "cleanup", "finished"]
# 现在所处的阶段.
# 状态机-like: 只有 prepare -> blocking -> cleanup 这个流程.
# finished 仅标记完成, 不表示阶段.


class LaunchableStatus(AbstractStandaloneStatus):
    stage: Optional[U_Stage] = None

    def __init__(self, id: str) -> None:
        self._id = id
        super().__init__()

    @property
    def id(self) -> str:
        return self._id

    @property
    def prepared(self) -> bool:
        return self.stage == "blocking"

    @property
    def blocking(self) -> bool:
        return self.stage == "blocking"

    @property
    def finished(self) -> bool:
        return self.stage == "finished"

    def unset(self) -> None:
        self.stage = None

    def set_prepare(self) -> None:
        self.update("prepare")

    def set_blocking(self) -> None:
        self.update("blocking")

    def set_cleanup(self) -> None:
        self.update("cleanup")

    def set_finished(self) -> None:
        self.update("finished")

    def frame(self):
        instance = LaunchableStatus(self.id)
        instance.stage = self.stage
        return instance

    def update(self, stage: U_Stage) -> None:
        past = self.frame()
        self.stage = stage
        self.notify(past)

    async def wait_for_prepared(self):
        while self.stage == "prepare" or self.stage is None:
            await self.wait_for_update()

    async def wait_for_completed(self):
        while self.stage != "cleanup":
            await self.wait_for_update()

    async def wait_for_finished(self):
        while self.stage != "finished":
            await self.wait_for_update()


class Launchable(metaclass=ABCMeta):
    id: str
    status: LaunchableStatus

    def __init__(self) -> None:
        self.status = LaunchableStatus(self.id)

    @property
    @abstractmethod
    def required(self) -> Set[str]:
        ...

    @property
    @abstractmethod
    def stages(self) -> Set[U_Stage]:
        ...

    @abstractmethod
    async def launch(self, manager: Launart):
        pass

    def on_require_prepared(self, components: Set[str]):
        pass

    def on_require_exited(self, components: Set[str]):
        pass


class RequirementResolveFailed(Exception):
    pass


def resolve_requirements(
    components: Set[Launchable],
) -> List[Set[Launchable]]:
    resolved = set()
    result = []
    while components:
        layer = {component for component in components if component.required.issubset(resolved)}

        if layer:
            components -= layer
            resolved.update(component.id for component in layer)
            result.append(layer)
        else:
            raise RequirementResolveFailed
    return result
