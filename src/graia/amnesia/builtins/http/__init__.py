try:
    from .aiohttp import AiohttpClientService as _AiohttpClientService
except ImportError:
    _AiohttpClientService = None

try:
    from .httpx import HttpxClientService as _HttpxClientService
except ImportError:
    _HttpxClientService = None

try:
    from .niquests import NiquestsClientService as _NiquestsClientService
except ImportError:
    _NiquestsClientService = None

try:
    from .pyreqwest import PyReqwestClientService as _PyReqwestClientService
except ImportError:
    _PyReqwestClientService = None

from launart import Launart
from .httptypes import Request, Response


async def request(payload: Request, *, stream: bool = False, chunk_size: int = 1024) -> Response:
    services = [_AiohttpClientService, _HttpxClientService, _NiquestsClientService, _PyReqwestClientService]
    services = [*filter(None, services)]
    if not services:
        raise RuntimeError("Please install at least one of them: `aiohttp`, `httpx`, `niquests`, `pyreqwest`")
    manager = Launart.current()
    for serv in services:
        try:
            client = manager.get_component(serv)
            return await client.request(payload, stream=stream, chunk_size=chunk_size)
        except ValueError:
            continue
    raise RuntimeError("Please install at least one of them: `aiohttp`, `httpx`, `niquests`, `pyreqwest`")


def __getattr__(name):
    if name == "AiohttpClientService":
        if _AiohttpClientService is None:
            raise ImportError("Please install `aiohttp` first. Install with `pip install graia-amnesia[aiohttp]`")
        return _AiohttpClientService
    if name == "HttpxClientService":
        if _HttpxClientService is None:
            raise ImportError("Please install `httpx` first. Install with `pip install graia-amnesia[httpx]`")
        return _HttpxClientService
    if name == "NiquestsClientService":
        if _NiquestsClientService is None:
            raise ImportError("Please install `niquests` first. Install with `pip install graia-amnesia[niquests]`")
        return _NiquestsClientService
    if name == "PyReqwestClientService":
        if _PyReqwestClientService is None:
            raise ImportError("Please install `pyreqwest` first. Install with `pip install graia-amnesia[pyreqwest]`")
        return _PyReqwestClientService
    if name == "request":
        return request
    if name == "Request":
        return Request
    if name == "Response":
        return Response
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
