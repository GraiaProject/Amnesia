import random
import string
from typing import Callable, Dict, Hashable, List, Set, Tuple, Type, TypeVar, Union

T = TypeVar("T")
H = TypeVar("H", bound=Hashable)


def priority_strategy(
    items: List[T],
    getter: Callable[
        [T],
        Union[
            Set[H],
            Dict[H, Union[int, float]],
            Tuple[Union[Set[H], Dict[H, Union[int, float]]], ...],
        ],
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


T = TypeVar("T")


class Registrar(Dict):
    def register(self, key):
        def decorator(method):
            self[key] = method
            return method

        return decorator

    def decorate(self, attr):
        def decorator(cls: Type[T]) -> Type[T]:
            getattr(cls, attr).update(self)
            return cls

        return decorator


def random_id(length=12):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))
