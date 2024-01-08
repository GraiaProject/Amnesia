from __future__ import annotations

try:
    import sqlalchemy as sa
except ImportError:
    raise ImportError(
        "dependency 'sqlalchemy' is required for sqlalchemy service\nplease install it or install 'graia-amnesia[sqla]'"
    )

from .model import Base as Base
from .service import SqlalchemyService as SqlalchemyService
