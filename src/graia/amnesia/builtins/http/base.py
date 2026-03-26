from abc import ABCMeta, abstractmethod
from typing import Generic, TypeVar, cast

from launart import Service
from launart.status import Phase

from .httptypes import Request, Response


TSession = TypeVar("TSession")


class HttpClientService(Service, Generic[TSession], metaclass=ABCMeta):
    id = "http.client"
    session: TSession

    def __init__(self, session: TSession | None = None, follow_redirects: bool = True) -> None:
        self.session = cast(TSession, session)
        self.follow_redirects = follow_redirects
        super().__init__()

    @property
    def stages(self) -> set[Phase]:
        return {"preparing", "cleanup"}

    @property
    def required(self):
        return set()

    @abstractmethod
    async def request(self, payload: Request, *, stream: bool = False, chunk_size: int = 1024) -> Response:
        raise NotImplementedError("base http client service does not implement request method")
