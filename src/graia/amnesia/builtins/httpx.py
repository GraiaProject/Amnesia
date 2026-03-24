from typing import cast

from launart import Launart, Service
from launart.status import Phase

from .http_model import Request, Response, Timeout

try:
    from httpx import AsyncClient
    from httpx import Timeout as ClientTimeout
except ImportError:
    raise ImportError(
        "dependency 'httpx' is required for httpx client service\nplease install it or install 'graia-amnesia[httpx]'"
    )


class HttpxClientService(Service):
    id = "http.client/httpx"
    session: AsyncClient

    def __init__(self, session: AsyncClient | None = None) -> None:
        self.session = cast(AsyncClient, session)
        super().__init__()

    @property
    def stages(self) -> set[Phase]:
        return {"preparing", "cleanup", "blocking"}

    @property
    def required(self):
        return set()

    async def launch(self, manager: Launart):
        async with self.stage("preparing"):
            if self.session is None:
                self.session = AsyncClient(timeout=ClientTimeout(timeout=None))
        async with self.stage("blocking"):
            await manager.status.wait_for_sigexit()
        async with self.stage("cleanup"):
            await self.session.aclose()

    async def request(self, payload: Request, *, stream: bool = False, chunk_size: int = 1024) -> Response:
        files = None
        if payload.files:
            files = {}
            for field, filename, content, content_type in payload.iter_normalized_files():
                if content_type is not None:
                    files[field] = (filename, content, content_type)
                else:
                    files[field] = (filename, content)

        if isinstance(payload.timeout, Timeout):
            timeout = ClientTimeout(
                timeout=payload.timeout.total,
                connect=payload.timeout.connect,
                read=payload.timeout.read,
            )
        else:
            timeout = ClientTimeout(payload.timeout)

        resp = await self.session.request(
            payload.method,
            payload.url,
            params={k: str(v) for k, v in payload.params.items() if v is not None} if payload.params else None,
            data=dict(payload.data) if isinstance(payload.data, list) else payload.data,
            content=payload.content,
            json=payload.json,
            files=files,
            cookies=payload.cookies_obj().jar,
            headers=payload.headers,
            timeout=timeout,
            follow_redirects=payload.follow_redirects,
            extensions=dict(payload.extensions),
        )
        if not stream:
            return Response(
                status_code=resp.status_code,
                request=payload,
                headers=resp.headers.copy(),
                stream=await resp.aread(),
                reason_phrase=resp.reason_phrase,
                extensions=resp.extensions,
                http_version=resp.http_version,
                _release=resp.aclose,
            )
        return Response(
            status_code=resp.status_code,
            request=payload,
            headers=resp.headers.copy(),
            stream=resp.aiter_bytes(chunk_size),
            reason_phrase=resp.reason_phrase,
            extensions=resp.extensions,
            http_version=resp.http_version,
            _release=resp.aclose,
        )
