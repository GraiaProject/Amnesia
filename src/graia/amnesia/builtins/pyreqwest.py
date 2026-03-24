from typing import cast

from launart import Launart, Service
from launart.status import Phase

try:
    from pyreqwest.client import Client, ClientBuilder
except ImportError:
    raise ImportError(
        "dependency 'pyreqwest' is required for pyreqwest client service\n"
        "please install it or install 'graia-amnesia[pyreqwest]'"
    )


class PyReqwestClientService(Service):
    id = "http.client/pyreqwest"
    session: Client

    def __init__(self, session: Client | None = None) -> None:
        self.session = cast(Client, session)
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
                self.session = ClientBuilder().build()

        async with self.stage("cleanup"):
            await self.session.close()
