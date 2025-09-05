import logging

from loguru import logger

try:
    from sqlalchemy.log import Identified, _qual_logger_name_for_cls
except ImportError:
    raise ImportError(
        "dependency 'sqlalchemy' is required for sqlalchemy service\nplease install it or install 'graia-amnesia[sqla]'"
    )

from ..utils import LoguruHandler, get_subclasses
from .model import Base as Base
from .service import SqlalchemyService as SqlalchemyService


def patch_logger(log_level: str | int = "INFO", sqlalchemy_echo: bool = False) -> None:
    handler = LoguruHandler()
    logging.getLogger("sqlalchemy").addHandler(handler)

    if isinstance(log_level, str):
        log_level = logger.level(log_level).no

    echo_log_level = log_level if sqlalchemy_echo else logging.WARNING

    levels = {
        "alembic": log_level,
        "sqlalchemy": log_level,
        **{_qual_logger_name_for_cls(cls): echo_log_level for cls in set(get_subclasses(Identified))},
    }

    for name, level in levels.items():
        logging.getLogger(name).setLevel(level)
