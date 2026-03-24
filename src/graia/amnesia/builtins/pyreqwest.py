from datetime import timedelta
from io import BytesIO
from typing import cast

from launart import Launart, Service
from launart.status import Phase

from .http_model import ByteStream, Request, Response, Timeout

try:
    from pyreqwest.client import Client, ClientBuilder
    from pyreqwest.multipart import FormBuilder, PartBuilder
except ImportError:
    raise ImportError(
        "dependency 'pyreqwest' is required for pyreqwest client service\n"
        "please install it or install 'graia-amnesia[pyreqwest]'"
    )


class PyReqwestClientService(Service):
    id = "http.client/pyreqwest"
    session: Client

    def __init__(self, session: Client | None = None, follow_redirects: bool = True) -> None:
        self.session = cast(Client, session)
        self.follow_redirects = follow_redirects
        super().__init__()

    @property
    def stages(self) -> set[Phase]:
        return {"preparing", "blocking", "cleanup"}

    @property
    def required(self):
        return set()

    async def launch(self, manager: Launart):
        async with self.stage("preparing"):
            if self.session is None:
                self.session = ClientBuilder().follow_redirects(self.follow_redirects).build()
        async with self.stage("blocking"):
            await manager.status.wait_for_sigexit()

        async with self.stage("cleanup"):
            await self.session.close()

    async def request(self, payload: Request, *, stream: bool = False, chunk_size: int = 1024) -> Response:
        files = None
        if payload.files:
            files = FormBuilder()
            for field, filename, content, content_type in payload.iter_normalized_files():
                part = PartBuilder.from_bytes(content if isinstance(content, bytes) else content.read())
                if filename is not None:
                    part.file_name(filename)
                if content_type is not None:
                    part.mime(content_type)
                files.part(field, part)

        if isinstance(payload.timeout, Timeout):
            timeout = timedelta(seconds=payload.timeout.total or 5)
        else:
            timeout = timedelta(seconds=payload.timeout or 5)

        req = (
            self.session.request(payload.method, payload.url)
            .query(payload.params or {})
            .headers(payload.headers)
            .timeout(timeout)
            .form(payload.data or {})
            .extensions(payload.extensions)
        )
        match payload.content:
            case str():
                req.body_text(payload.content)
            case bytes():
                req.body_bytes(payload.content)
            case _:
                if payload.content:
                    req.body_stream(payload.content)
        if payload.json:
            req.body_json(payload.json)
        if files:
            req.multipart(files)
        resp = await req.build().send()
        if not stream:
            return Response(
                status_code=resp.status,
                request=payload,
                headers=resp.headers.copy(),
                stream=BytesIO(await resp.bytes()),
                extensions=resp.extensions,
                http_version=resp.version,
            )

        async def chuck_iter():
            reader = resp.body_reader
            chuck = await reader.read(chunk_size)
            if chuck is None:
                yield b""
                return
            while chuck is not None:
                yield chuck.to_bytes()
                chuck = await reader.read(chunk_size)

        return Response(
            status_code=resp.status,
            request=payload,
            headers=resp.headers.copy(),
            stream=chuck_iter(),
            extensions=resp.extensions,
            http_version=resp.version,
        )
