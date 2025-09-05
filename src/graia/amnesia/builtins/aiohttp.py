from typing import cast

from launart import Launart, Service
from launart.status import Phase

try:
    from aiohttp import ClientSession, ClientTimeout
except ImportError:
    raise ImportError(
        "dependency 'aiohttp' is required for aiohttp client service\n"
        "please install it or install 'graia-amnesia[aiohttp]'"
    )


class AiohttpClientService(Service):
    id = "http.client/aiohttp"
    session: ClientSession

    def __init__(self, session: ClientSession | None = None) -> None:
        self.session = cast(ClientSession, session)
        super().__init__()

    @property
    def stages(self) -> set[Phase]:
        return {"preparing", "cleanup"}

    @property
    def required(self):
        return set()

    async def launch(self, manager: Launart):
        async with self.stage("preparing"):
            if self.session is None:
                self.session = ClientSession(timeout=ClientTimeout(total=None))
        async with self.stage("cleanup"):
            await self.session.close()
