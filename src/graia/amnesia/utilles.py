import logging
import random
import string
from logging import LogRecord
from types import FrameType
from typing import (
    Callable,
    Dict,
    Hashable,
    List,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from loguru import logger
from loguru._logger import Core
from rich.console import ConsoleRenderable
from rich.logging import RichHandler
from rich.text import Text

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


for lv in Core().levels.values():
    logging.addLevelName(lv.no, lv.name)


class LoguruHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = cast(FrameType, frame.f_back)
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def highlight(attr: str) -> Dict[str, Callable[[Text], Text]]:
    """附加 attr 给文本.

    Example:
    ```py
    logger.warning("Sth is happening!", **highlight("red bold"))
    ```
    """

    def highlighter(text: Text) -> Text:
        return Text.from_markup(f"[{attr}]{text.plain}[/{attr}]")

    return {"highlighter": highlighter}


class LoguruRichHandler(RichHandler):
    """
    使用更好的方式操纵 RichHandler

    Example:

    ```py
    logger.warning("Sth is happening!", render_attr="red bold")
    logger.warning("Sth is happening!", **highlight("red bold"))
    logger.warning("Sth is happening!", alt="[red bold]Sth is happening![/red bold]")
    ```
    """

    def render_message(self, record: LogRecord, message: str) -> "ConsoleRenderable":
        extra: dict = getattr(record, "extra", {})
        if "render_attr" in extra:
            record.__dict__.update(highlight(extra["render_attr"]))
        elif "highlighter" in extra:
            record.highlighter = extra["highlighter"]  # type: ignore
        if "alt" in extra:
            message = extra["alt"]
            record.markup = True  # type: ignore
        if "markup" in extra:
            record.markup = extra["markup"]  # type: ignore
        return super().render_message(record, message)
