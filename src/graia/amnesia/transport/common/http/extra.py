from dataclasses import dataclass
from typing import Dict, Literal

import yarl

from graia.amnesia.transport.interface import ExtraContent


@dataclass
class HttpRequest(ExtraContent):
    headers: Dict[str, str]
    cookies: Dict[str, str]
    query_params: Dict[str, str]
    url: yarl.URL
    host: str
    method: 'Literal["GET", "POST", "PUT", "DELETE"] | str'
    client_ip: str
    client_port: int


@dataclass
class HttpResponse(ExtraContent):
    status: int
    headers: Dict[str, str]
    cookies: Dict[str, str]
    uri: yarl.URL
