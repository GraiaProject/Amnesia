from typing import Any, Dict, Optional, Tuple, TypedDict, Union

from typing_extensions import NotRequired, Unpack

T_HttpResponse = Union[Tuple[Any, Unpack[Tuple[Dict[str, Any], ...]]], Any]


def status(code: int):
    return {"status": code}


def headers(headers: Dict[str, str]):
    return {"headers": headers}


def cookies(cookies: Dict[str, str], expires: Optional[int] = None):
    return {"cookies": cookies, "cookie_expires": expires}


class HttpServerResponseDescription(TypedDict):
    status: NotRequired[int]
    headers: NotRequired[Dict[str, str]]
    cookies: NotRequired[Dict[str, str]]
    cookie_expires: NotRequired[Optional[int]]


class Response:
    body: Any
    description: HttpServerResponseDescription

    def __init__(self, response_body: Any, *desc: Dict[str, Any]):
        self.body = response_body
        self.description = {}
        for i in desc:
            self.description.update(i)  # type: ignore
