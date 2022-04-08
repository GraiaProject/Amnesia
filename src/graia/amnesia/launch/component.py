from typing import TYPE_CHECKING, Any, Callable, Coroutine, List, Optional, Set

if TYPE_CHECKING:
    from graia.amnesia.launch.manager import LaunchManager


class LaunchComponent:
    id: str
    required: Set[str]

    prepare: Optional[Callable[["LaunchManager"], Coroutine[None, None, Any]]] = None
    mainline: Optional[Callable[["LaunchManager"], Coroutine[None, None, Any]]] = None
    cleanup: Optional[Callable[["LaunchManager"], Coroutine[None, None, Any]]] = None

    def __init__(
        self,
        component_id: str,
        required: Set[str],
        mainline: Optional[Callable[["LaunchManager"], Coroutine[None, None, Any]]] = None,
        prepare: Optional[Callable[["LaunchManager"], Coroutine[None, None, Any]]] = None,
        cleanup: Optional[Callable[["LaunchManager"], Coroutine[None, None, Any]]] = None,
    ):
        self.id = component_id
        self.required = required
        self.mainline = mainline
        self.prepare = prepare
        self.cleanup = cleanup


class RequirementResolveFailed(Exception):
    pass


def resolve_requirements(
    components: Set[LaunchComponent],
) -> List[Set[LaunchComponent]]:
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
