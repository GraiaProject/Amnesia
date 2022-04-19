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
    priorities_cache = {}
    for item in items:
        pattern = getter(item)
        if isinstance(pattern, Set):
            for content in pattern:
                if content in priorities_cache:
                    raise ValueError(
                        f"{content} which is an unlocated item is already existed, and it conflicts with {result[content]}"
                    )
                priorities_cache[content] = ...
                result[content] = item
        elif isinstance(pattern, Dict):
            for content, priority in pattern.items():
                if content in priorities_cache:
                    if priorities_cache[content] is ...:
                        raise ValueError(
                            f"{content} is already existed, and it conflicts with {result[content]}, an unlocated item."
                        )
                    if priority is ...:
                        raise ValueError(
                            f"{content} which is an unlocated item is already existed, and it conflicts with {result[content]}"
                        )
                    if priorities_cache[content] < priority:
                        priorities_cache[content] = priority
                        result[content] = item
                else:
                    priorities_cache[content] = priority
                    result[content] = item
        elif isinstance(pattern, Tuple):
            for subpattern in pattern:
                if isinstance(subpattern, Set):
                    for content in subpattern:
                        if content in priorities_cache:
                            raise ValueError(
                                f"{content} which is an unlocated item is already existed, and it conflicts with {result[content]}"
                            )
                        priorities_cache[content] = ...
                        result[content] = item
                elif isinstance(subpattern, Dict):
                    for content, priority in subpattern.items():
                        if content in priorities_cache:
                            if priorities_cache[content] is ...:
                                raise ValueError(
                                    f"{content} is already existed, and it conflicts with {result[content]}, an unlocated item."
                                )
                            if priority is ...:
                                raise ValueError(
                                    f"{content} which is an unlocated item is already existed, and it conflicts with {result[content]}"
                                )
                            if priorities_cache[content] < priority:
                                priorities_cache[content] = priority
                                result[content] = item
                        else:
                            priorities_cache[content] = priority
                            result[content] = item
                else:
                    raise TypeError(f"{subpattern} is not a valid pattern.")
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
