from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator, Mapping, MutableMapping
from dataclasses import dataclass, field
from http.cookiejar import Cookie, CookieJar
from json import JSONDecodeError
from json import loads as json_loads
from typing import IO, Any, Awaitable, Protocol, TypeAlias, TypedDict, runtime_checkable
from typing_extensions import NotRequired

JSONType: TypeAlias = dict[str, "JSONType"] | list["JSONType"] | str | int | float | bool | None
HeadersType: TypeAlias = Mapping[str, str]
QueryType: TypeAlias = Mapping[str, str | int | float | bool]
ExtensionsType: TypeAlias = Mapping[str, Any]
FormDataType: TypeAlias = Mapping[str, Any] | list[tuple[str, Any]] | None
CookieTypes: TypeAlias = Mapping[str, str] | CookieJar | list[tuple[str, str]] | None


@runtime_checkable
class ByteStream(Protocol):
    def __iter__(self) -> Iterator[bytes]: ...


@runtime_checkable
class AsyncByteStream(Protocol):
    def __aiter__(self) -> AsyncIterator[bytes]: ...


FileContent: TypeAlias = IO[bytes] | bytes


class FileType(TypedDict):
    content: FileContent
    filename: NotRequired[str | None]
    content_type: NotRequired[str | None]


FileTypeTuple: TypeAlias = FileContent | tuple[str | None, FileContent] | tuple[str | None, FileContent, str | None]

FilesTypes: TypeAlias = (
    dict[str, FileType] | list[tuple[str, FileType]] | dict[str, FileTypeTuple] | list[tuple[str, FileTypeTuple]] | None
)


@dataclass(slots=True)
class Timeout:
    total: float | None = None
    connect: float | None = None
    read: float | None = None


class HTTPError(Exception):
    """Base error for unified HTTP model."""


class RequestError(HTTPError):
    """Raised for invalid request composition or request-stage failures."""


class StreamConsumedError(HTTPError):
    """Raised when a non-replayable stream cannot be consumed as requested."""


class ResponseDecodeError(HTTPError):
    """Raised when decoding bytes into text/json fails."""


class HTTPStatusError(HTTPError):
    """Raised for 4xx/5xx HTTP responses after status checking."""

    def __init__(
        self,
        message: str,
        request: Request | None,
        response: Response,
    ) -> None:
        super().__init__(message)
        self.request = request
        self.response = response


@dataclass(frozen=True, slots=True)
class Request:
    method: str
    url: str

    params: QueryType | None = None
    headers: HeadersType = field(default_factory=dict)
    cookies: CookieTypes = None

    content: bytes | str | ByteStream | AsyncByteStream | None = None
    data: FormDataType = None
    json: JSONType | None = None
    files: FilesTypes = None

    timeout: float | Timeout | None = 5.0
    proxy: str | Mapping[str, str] | None = None
    follow_redirects: bool = False
    extensions: ExtensionsType = field(default_factory=dict)

    def __post_init__(self) -> None:
        channels = (self.content is not None, self.json is not None, self.files is not None)
        if sum(1 for active in channels if active) > 1:
            raise RequestError("conflicting request body channels: use only one of content/json/files")

    def iter_normalized_files(
        self,
    ) -> Iterator[tuple[str, str | None, FileContent, str | None]]:
        """
        Yield multipart entries as: (field_name, filename, content, content_type).
        """
        if self.files is None:
            return

        if isinstance(self.files, Mapping):
            items = self.files.items()
        else:
            items = self.files

        for name, raw in items:
            filename, content, content_type = self._normalize_file_value(name, raw)
            yield name, filename, content, content_type

    @staticmethod
    def _normalize_file_value(
        field_name: str,
        raw: FileType | FileTypeTuple,
    ) -> tuple[str | None, FileContent, str | None]:
        if isinstance(raw, dict):
            if "content" not in raw:
                raise RequestError(f"multipart field '{field_name}' missing required key: content")
            return raw.get("filename"), raw["content"], raw.get("content_type")

        if isinstance(raw, tuple):
            if len(raw) == 2:
                filename, content = raw
                return filename, content, None
            if len(raw) == 3:
                filename, content, content_type = raw
                return filename, content, content_type
            raise RequestError(f"invalid multipart tuple size for field '{field_name}', expected 2 or 3")

        return None, raw, None

    def cookies_obj(self) -> Cookies:
        return Cookies(self.cookies)

    def cookie_header(self) -> str | None:
        return self.cookies_obj().to_cookie_header()


@dataclass(slots=True)
class Response:
    status_code: int
    request: Request | None = None
    headers: HeadersType = field(default_factory=dict)
    reason_phrase: str = ""
    http_version: str = "HTTP/1.1"

    stream: bytes | ByteStream | AsyncByteStream | None = None
    extensions: MutableMapping[str, Any] = field(default_factory=dict)
    json_loader: Callable[[str], Any] = json_loads

    _release: Callable[[], Awaitable[None]] | None = field(default=None)
    _content_cache: bytes | None = field(init=False, default=None, repr=False)
    _text_cache: dict[tuple[str, str], str] = field(init=False, default_factory=dict, repr=False)

    @property
    def is_informational(self) -> bool:
        return 100 <= self.status_code <= 199

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code <= 299

    @property
    def is_redirect(self) -> bool:
        return 300 <= self.status_code <= 399

    @property
    def is_client_error(self) -> bool:
        return 400 <= self.status_code <= 499

    @property
    def is_server_error(self) -> bool:
        return 500 <= self.status_code <= 599

    @property
    def is_error(self) -> bool:
        return self.is_client_error or self.is_server_error

    @property
    def content(self) -> bytes:
        return self.read()

    @property
    def text(self) -> str:
        return self.decode_text()

    def read(self) -> bytes:
        if self._content_cache is not None:
            return self._content_cache

        if self.stream is None:
            self._content_cache = ans = b""
            return ans

        if isinstance(self.stream, bytes):
            self._content_cache = ans = self.stream
            return ans

        if isinstance(self.stream, ByteStream) and not isinstance(self.stream, AsyncByteStream):
            self._content_cache = ans = b"".join(self.stream)
            return ans

        raise StreamConsumedError("cannot read() an async stream from sync context; use aread() instead")

    async def aread(self) -> bytes:
        if self._content_cache is not None:
            return self._content_cache

        if self.stream is None:
            self._content_cache = ans = b""
            return ans

        if isinstance(self.stream, bytes):
            self._content_cache = ans = self.stream
            return ans

        if isinstance(self.stream, AsyncByteStream):
            chunks: list[bytes] = []
            async for chunk in self.stream:
                chunks.append(chunk)
            self._content_cache = ans = b"".join(chunks)
            return ans

        if isinstance(self.stream, ByteStream):
            self._content_cache = ans = b"".join(self.stream)
            return ans

        raise StreamConsumedError("response stream is not readable")

    def iter_bytes(self, chunk_size: int = 65536) -> Iterator[bytes]:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")

        if self._content_cache is not None:
            for i in range(0, len(self._content_cache), chunk_size):
                yield self._content_cache[i : i + chunk_size]
            return

        if self.stream is None:
            self._content_cache = b""
            return

        if isinstance(self.stream, bytes):
            self._content_cache = self.stream
            for i in range(0, len(self.stream), chunk_size):
                yield self._content_cache[i : i + chunk_size]
            return

        if isinstance(self.stream, ByteStream) and not isinstance(self.stream, AsyncByteStream):
            cache: list[bytes] = []
            for chunk in self.stream:
                cache.append(chunk)
                yield chunk
            self._content_cache = b"".join(cache)
            return

        raise StreamConsumedError("cannot iter_bytes() an async stream from sync context; use aiter_bytes()")

    async def aiter_bytes(self, chunk_size: int = 65536) -> AsyncIterator[bytes]:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")

        if self._content_cache is not None:
            for i in range(0, len(self._content_cache), chunk_size):
                yield self._content_cache[i : i + chunk_size]
            return

        if self.stream is None:
            self._content_cache = b""
            return

        if isinstance(self.stream, bytes):
            self._content_cache = self.stream
            for i in range(0, len(self.stream), chunk_size):
                yield self._content_cache[i : i + chunk_size]
            return

        if isinstance(self.stream, AsyncByteStream):
            cache: list[bytes] = []
            async for chunk in self.stream:
                cache.append(chunk)
                yield chunk
            self._content_cache = b"".join(cache)
            return

        if isinstance(self.stream, ByteStream):
            cache: list[bytes] = []
            for chunk in self.stream:
                cache.append(chunk)
                yield chunk
            self._content_cache = b"".join(cache)
            return

        raise StreamConsumedError("response stream is not readable")

    def iter_lines(self, keepends: bool = False) -> Iterator[str]:
        text = self.decode_text()
        for line in text.splitlines(keepends=keepends):
            yield line

    async def aiter_lines(self, keepends: bool = False) -> AsyncIterator[str]:
        text = await self.adecode_text()
        for line in text.splitlines(keepends=keepends):
            yield line

    def decode_text(self, encoding: str | None = None, errors: str = "replace") -> str:
        chosen = encoding or self._get_encoding_from_headers() or "utf-8"
        cache_key = (chosen, errors)
        if cache_key in self._text_cache:
            return self._text_cache[cache_key]

        data = self.read()
        try:
            text = data.decode(chosen, errors=errors)
        except LookupError as e:
            raise ResponseDecodeError(f"unknown encoding: {chosen}") from e

        self._text_cache[cache_key] = text
        return text

    async def adecode_text(self, encoding: str | None = None, errors: str = "replace") -> str:
        chosen = encoding or self._get_encoding_from_headers() or "utf-8"
        cache_key = (chosen, errors)
        if cache_key in self._text_cache:
            return self._text_cache[cache_key]

        data = await self.aread()
        try:
            text = data.decode(chosen, errors=errors)
        except LookupError as e:
            raise ResponseDecodeError(f"unknown encoding: {chosen}") from e

        self._text_cache[cache_key] = text
        return text

    def json(self) -> Any:
        try:
            return self.json_loader(self.decode_text())
        except JSONDecodeError as e:
            raise ResponseDecodeError("response body is not valid JSON") from e

    async def ajson(self) -> Any:
        try:
            return self.json_loader(await self.adecode_text())
        except JSONDecodeError as e:
            raise ResponseDecodeError("response body is not valid JSON") from e

    def raise_for_status(self) -> None:
        if not self.is_error:
            return

        req = self.request
        target = req.url if req is not None else "<unknown>"
        message = f"{self.status_code} response for {target}"
        raise HTTPStatusError(message, req, self)

    def _get_encoding_from_headers(self) -> str | None:
        content_type = None
        for key, value in self.headers.items():
            if key.lower() == "content-type":
                content_type = value
                break

        if not content_type:
            return None

        parts = [part.strip() for part in content_type.split(";")]
        for part in parts[1:]:
            if part.lower().startswith("charset="):
                charset = part.split("=", 1)[1].strip().strip('"')
                return charset or None
        return None

    async def __aenter__(self):
        return self

    async def __aiter__(self) -> AsyncIterator[bytes]:
        async for chunk in self.aiter_bytes():
            yield chunk

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._release:
            await self._release()


class Cookies(Mapping[str, str]):
    """Cookie container compatible with Mapping/CookieJar/list tuple inputs."""

    jar: CookieJar
    __slots__ = ("jar",)

    def __init__(self, cookies: CookieTypes = None) -> None:
        if isinstance(cookies, CookieJar):
            self.jar = cookies
            return

        self.jar = CookieJar()
        if isinstance(cookies, Mapping):
            for k, v in cookies.items():
                self._set_cookie(str(k), str(v))
        elif isinstance(cookies, list):
            for k, v in cookies:
                self._set_cookie(str(k), str(v))

    def _set_cookie(self, name: str, value: str) -> None:
        cookie = Cookie(
            version=0,
            name=name,
            value=value,
            port=None,
            port_specified=False,
            domain="",
            domain_specified=False,
            domain_initial_dot=False,
            path="/",
            path_specified=False,
            secure=False,
            expires=None,
            discard=True,
            comment=None,
            comment_url=None,
            rest={},
            rfc2109=False,
        )
        self.jar.set_cookie(cookie)

    def __getitem__(self, name: str) -> str:
        for cookie in self.jar:
            if cookie.name == name and cookie.value is not None:
                return cookie.value
        raise KeyError(name)

    def __iter__(self) -> Iterator[str]:
        return iter({cookie.name for cookie in self.jar})

    def __len__(self) -> int:
        return sum(1 for _ in self.jar)

    def to_cookie_header(self) -> str | None:
        pairs = [f"{cookie.name}={cookie.value}" for cookie in self.jar if cookie.value is not None]
        if not pairs:
            return None
        return "; ".join(pairs)
