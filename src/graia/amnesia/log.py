import logging
import sys
from logging import LogRecord
from types import FrameType, TracebackType
from typing import Any, Callable, Dict, Optional, Type, cast

from loguru import logger
from loguru._logger import Core
from rich.console import Console, ConsoleRenderable
from rich.logging import RichHandler
from rich.text import Text

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


def highlight(style: str) -> Dict[str, Callable[[Text], Text]]:
    """Add `style` to RichHandler's log text.

    Example:
    ```py
    logger.warning("Sth is happening!", **highlight("red bold"))
    ```
    """

    def highlighter(text: Text) -> Text:
        return Text(text.plain, style=style)

    return {"highlighter": highlighter}


class LoguruRichHandler(RichHandler):
    """
    Interpolate RichHandler in a better way

    Example:

    ```py
    logger.warning("Sth is happening!", style="red bold")
    logger.warning("Sth is happening!", **highlight("red bold"))
    logger.warning("Sth is happening!", alt="[red bold]Sth is happening![/red bold]")
    logger.warning("Sth is happening!", text=Text.from_markup("[red bold]Sth is happening![/red bold]"))
    ```
    """

    def render_message(self, record: LogRecord, message: str) -> "ConsoleRenderable":
        extra: dict = getattr(record, "extra", {})
        if "style" in extra:
            record.__dict__.update(highlight(extra["style"]))
        elif "highlighter" in extra:
            setattr(record, "highlighter", extra["highlighter"])
        if "alt" in extra:
            message = extra["alt"]
            setattr(record, "markup", True)
        if "markup" in extra:
            setattr(record, "markup", extra["markup"])
        if "text" in extra:
            setattr(record, "highlighter", lambda _: extra["text"])
        return super().render_message(record, message)


ExceptionHook = Callable[[Type[BaseException], BaseException, Optional[TracebackType]], Any]


def _loguru_exc_hook(typ: Type[BaseException], val: BaseException, tb: Optional[TracebackType]):
    logger.opt(exception=(typ, val, tb)).error("Exception:")


def install(rich_console: Console, exc_hook: Optional[ExceptionHook] = _loguru_exc_hook) -> None:
    """Install Rich logging and Loguru exception hook"""
    logger.configure(
        handlers=[
            {
                "sink": LoguruRichHandler(console=rich_console, rich_tracebacks=True, tracebacks_show_locals=True),
                "format": lambda _: "{message}",
                "level": 0,
            }
        ]
    )
    if exc_hook is not None:
        sys.excepthook = exc_hook
