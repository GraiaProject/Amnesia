from typing import cast

from launart import Launart

from .base import HttpClientService
from .httptypes import Request, Response, Timeout

try:
    from niquests import AsyncSession
    from urllib3 import Timeout as ClientTimeout
except ImportError:
    raise ImportError(
        "dependency 'niquests' is required for niquests client service\n"
        "please install it or install 'graia-amnesia[niquests]'"
    )

VERSIONS = {11: "HTTP/1.1", 20: "HTTP/2.0", 30: "HTTP/3.0"}


class NiquestsClientService(HttpClientService[AsyncSession]):
    id = "http.client/niquests"

    async def launch(self, manager: Launart):
        async with self.stage("preparing"):
            if self.session is None:
                self.session = AsyncSession()
        async with self.stage("cleanup"):
            await self.session.close()

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
                total=payload.timeout.total,
                connect=payload.timeout.connect,
                read=payload.timeout.read,
            )
        else:
            timeout = ClientTimeout(payload.timeout)
        if not stream:

            resp = await self.session.request(
                payload.method,
                payload.url,
                params={k: str(v) for k, v in payload.params.items() if v is not None} if payload.params else None,
                data=payload.content,
                json=payload.json,
                files=files,
                cookies=payload.cookies_obj().jar,
                headers=dict(payload.headers),
                proxies={"http": payload.proxy} if isinstance(payload.proxy, str) else None,
                timeout=timeout,
                stream=False,
                allow_redirects=payload.follow_redirects or self.follow_redirects,
            )
            return Response(
                status_code=resp.status_code or 200,
                request=payload,
                headers=resp.headers.copy(),
                stream=resp.content,
                reason_phrase=resp.reason or "",
                http_version=VERSIONS[resp.http_version or 11],
            )
        resp = await self.session.request(
            payload.method,
            payload.url,
            params={k: str(v) for k, v in payload.params.items() if v is not None} if payload.params else None,
            data=payload.content,
            json=payload.json,
            files=files,
            cookies=payload.cookies_obj().jar,
            headers=dict(payload.headers),
            proxies={"http": payload.proxy} if isinstance(payload.proxy, str) else None,
            timeout=timeout,
            stream=True,
            allow_redirects=payload.follow_redirects or self.follow_redirects,
        )
        return Response(
            status_code=resp.status_code or 200,
            request=payload,
            headers=resp.headers.copy(),
            stream=await resp.iter_content(chunk_size=chunk_size),
            reason_phrase=resp.reason or "",
            http_version=VERSIONS[resp.http_version or 11],
            _release=resp.close,
        )
