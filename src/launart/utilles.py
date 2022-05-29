from __future__ import annotations

import asyncio
from typing import (
    Callable,
    Coroutine,
    Dict,
    Hashable,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)

T = TypeVar("T")
H = TypeVar("H", bound=Hashable)

PriorityType = Union[
    Set[T],
    Dict[T, Union[int, float]],
    Tuple[
        Union[
            Set[T],
            Dict[T, Union[int, float]],
        ],
        ...,
    ],
]


def priority_strategy(
    items: List[T],
    getter: Callable[
        [T],
        PriorityType[H],
    ],
) -> Dict[H, T]:
    result = {}
    _cache = {}

    def _raise_conflict(content):
        raise ValueError(
            f"{content} which is an unlocated item is already existed, and it conflicts with {result[content]}"
        )

    def _raise_existed(content):
        raise ValueError(f"{content} is already existed, and it conflicts with {result[content]}, an unlocated item.")

    def _handle(pattern):
        if isinstance(pattern, Set):
            for content in pattern:
                if content in _cache:
                    _raise_conflict(content)
                _cache[content] = ...
                result[content] = item
        elif isinstance(pattern, Dict):
            for content, priority in pattern.items():
                if content in _cache:
                    if _cache[content] is ...:
                        _raise_existed(content)
                    if priority is ...:
                        _raise_conflict(content)
                    if _cache[content] < priority:
                        _cache[content] = priority
                        result[content] = item
                else:
                    _cache[content] = priority
                    result[content] = item
        else:
            raise TypeError(f"{pattern} is not a valid pattern.")

    for item in items:
        pattern = getter(item)
        if isinstance(pattern, (dict, set)):
            _handle(pattern)
        elif isinstance(pattern, tuple):
            for subpattern in pattern:
                _handle(subpattern)
        else:
            raise TypeError(f"{pattern} is not a valid pattern.")
    return result


async def wait_fut(
    coros: Iterable[Union[Coroutine, asyncio.Task]],
    *,
    timeout: Optional[float] = None,
    return_when: str = asyncio.ALL_COMPLETED,
) -> None:
    tasks = []
    for c in coros:
        if asyncio.iscoroutine(c):
            tasks.append(asyncio.create_task(c))
        else:
            tasks.append(c)
    if tasks:
        await asyncio.wait(tasks, timeout=timeout, return_when=return_when)
