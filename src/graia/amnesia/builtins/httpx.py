from typing import cast
from typing_extensions import deprecated

from launart import Launart, Service
from launart.status import Phase

try:
    from httpx import AsyncClient
    from httpx import Timeout as ClientTimeout
except ImportError:
    raise ImportError(
        "dependency 'httpx' is required for httpx client service\nplease install it or install 'graia-amnesia[httpx]'"
    )


@deprecated("`graia.amnesia.builtins.HttpxClientService` has moved to `graia.amnesia.builtins.http`.")
class HttpxClientService(Service):
    id = "http.client/httpx"
    session: AsyncClient

    def __init__(self, session: AsyncClient | None = None) -> None:
        self.session = cast(AsyncClient, session)
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
                self.session = AsyncClient(timeout=ClientTimeout(timeout=None))
        async with self.stage("cleanup"):
            await self.session.aclose()
