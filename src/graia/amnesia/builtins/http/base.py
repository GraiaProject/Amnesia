from abc import ABCMeta, abstractmethod

from launart import Service
from launart.status import Phase

from .httptypes import Request, Response


class HttpClientService(Service, metaclass=ABCMeta):
    id = "http.client"

    def __init__(self, follow_redirects: bool = True) -> None:
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
