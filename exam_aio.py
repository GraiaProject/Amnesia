import asyncio

from creart import it
from launart import Launart, Service
from launart.status import Phase

from graia.amnesia.builtins.http import request
from graia.amnesia.builtins.http.aiohttp import AiohttpClientService

# from graia.amnesia.builtins.http.httpx import HttpxClientService
# from graia.amnesia.builtins.http.niquests import NiquestsClientService
# from graia.amnesia.builtins.http.pyreqwest import PyReqwestClientService
from graia.amnesia.builtins.http.httptypes import HTTPStatusError, Request

manager = it(Launart)
manager.add_component(AiohttpClientService())


class MainService(Service):
    id = "main"

    @property
    def required(self):
        return set()

    @property
    def stages(self) -> set[Phase]:
        return {"blocking"}

    async def launch(self, manager: Launart) -> None:
        async with self.stage("blocking"):
            await asyncio.sleep(2)
            resp = await request(Request("GET", "https://httpbin.org/get"))
            print(resp.status_code)
            print(await resp.aread())
            print(await resp.ajson())
            resp1 = await request(Request("GET", "https://httpbin.org/image"), stream=True)
            async for chunk in resp1.aiter_bytes(1024):
                print(f"chunk: {len(chunk)} bytes")
            try:
                async with await request(Request("GET", "https://httpbin.org/status/404")) as resp:
                    resp.raise_for_status()
            except HTTPStatusError as e:
                print(e)


manager.add_component(MainService())
manager.launch_blocking()
