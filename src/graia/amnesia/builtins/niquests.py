from typing import cast

from launart import Launart, Service
from launart.status import Phase

try:
    from niquests import AsyncSession
except ImportError:
    raise ImportError(
        "dependency 'niquests' is required for niquests client service\n"
        "please install it or install 'graia-amnesia[niquests]'"
    )


class NiquestsClientService(Service):
    id = "http.client/niquests"
    session: AsyncSession

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = cast(AsyncSession, session)
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
                self.session = AsyncSession()
        async with self.stage("cleanup"):
            await self.session.close()
