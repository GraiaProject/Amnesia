import logging
import sys

from loguru import logger


class LoguruHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).patch(lambda rec: rec.update(name=record.name)).log(
            level, record.getMessage()
        )


def get_subclasses(cls):
    yield from cls.__subclasses__()
    for subclass in cls.__subclasses__():
        yield from get_subclasses(subclass)
