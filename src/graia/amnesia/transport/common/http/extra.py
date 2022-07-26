from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from yarl import URL

from graia.amnesia.transport.interface import ExtraContent


@dataclass
class HttpRequest(ExtraContent):
    headers: dict[str, str]
    cookies: dict[str, str]
    query_params: dict[str, str]
    url: URL
    host: str
    method: Literal["GET", "POST", "PUT", "DELETE"] | str
    client_ip: str
    client_port: int


@dataclass
class HttpResponse(ExtraContent):
    status: int
    headers: dict[str, str]
    cookies: dict[str, str]
    uri: URL
