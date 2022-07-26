from __future__ import annotations

from typing import Any, TypedDict, Union

from typing_extensions import NotRequired, Unpack

T_HttpResponse = Union["tuple[Any, Unpack[tuple[dict[str, Any], ...]]]", Any]


def status(code: int):
    return {"status": code}


def headers(headers: dict[str, str]):
    return {"headers": headers}


def cookies(cookies: dict[str, str], expires: int | None = None):
    return {"cookies": cookies, "cookie_expires": expires}


class HttpServerResponseDescription(TypedDict):
    status: NotRequired[int]
    headers: NotRequired[dict[str, str]]
    cookies: NotRequired[dict[str, str]]
    cookie_expires: NotRequired[int | None]


class Response:
    body: Any
    description: HttpServerResponseDescription

    def __init__(self, response_body: Any, *desc: dict[str, Any]):
        self.body = response_body
        self.description = {}
        for i in desc:
            self.description.update(i)  # type: ignore
