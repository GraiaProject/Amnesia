from .aiohttp import AiohttpClientService as AiohttpClientService
from .httptypes import Request, Response
from .httpx import HttpxClientService as HttpxClientService
from .niquests import NiquestsClientService as NiquestsClientService
from .pyreqwest import PyReqwestClientService as PyReqwestClientService

async def request(payload: Request, *, stream: bool = False, chunk_size: int = 1024) -> Response: ...
