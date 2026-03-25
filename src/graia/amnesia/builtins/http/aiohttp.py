from typing import cast

from launart import Launart, Service
from launart.status import Phase

from .httptypes import Request, Response, Timeout

try:
    from aiohttp import ClientSession, ClientTimeout, FormData
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

    async def request(self, payload: Request, *, stream: bool = False, chunk_size: int = 1024) -> Response:
        data = payload.data
        if payload.files:
            data = FormData(data or {}, quote_fields=False)
            for field, filename, content, content_type in payload.iter_normalized_files():
                data.add_field(field, content, filename=filename, content_type=content_type)
        cookies = ((cookie.name, cookie.value) for cookie in payload.cookies_obj().jar if cookie.value is not None)

        if isinstance(payload.timeout, Timeout):
            timeout = ClientTimeout(
                total=payload.timeout.total,
                connect=payload.timeout.connect,
                sock_read=payload.timeout.read,
            )
        else:
            timeout = ClientTimeout(payload.timeout)

        resp = await self.session._request(
            payload.method,
            payload.url,
            params={k: str(v) for k, v in payload.params.items() if v is not None} if payload.params else None,
            data=payload.content or data,
            json=payload.json,
            cookies=cookies,
            headers=payload.headers,
            proxy=(
                payload.proxy
                if isinstance(payload.proxy, str)
                else next(iter(payload.proxy.values())) if payload.proxy else None
            ),
            timeout=timeout,
            allow_redirects=payload.follow_redirects,
        )
        if not stream:
            ans = Response(
                status_code=resp.status,
                request=payload,
                headers=resp.headers.copy(),
                stream=await resp.read(),
                reason_phrase=resp.reason or "",
            )
            resp.release()
            await resp.wait_for_close()
            return ans

        async def chuck_iter():
            try:
                async for chunk in resp.content.iter_chunked(chunk_size):
                    yield chunk
            finally:
                resp.release()
                await resp.wait_for_close()

        async def close():
            await resp.__aexit__(None, None, None)

        return Response(
            status_code=resp.status,
            request=payload,
            headers=resp.headers.copy(),
            stream=chuck_iter(),
            reason_phrase=resp.reason or "",
            _release=close,
        )
