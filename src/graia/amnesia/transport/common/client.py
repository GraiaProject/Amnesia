from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Any, Generic, TypeVar

from launart.service import ExportInterface, Service, TService

from graia.amnesia.json import TJson
from graia.amnesia.transport.rider import TransportRider

T = TypeVar("T", bound="AbstractClientService")


class AbstractClientInterface(ExportInterface[T], metaclass=ABCMeta):
    @abstractmethod
    def request(
        self,
        method: str,
        url: str,
        params: dict | None = None,
        data: Any = None,
        headers: dict | None = None,
        cookies: dict | None = None,
        timeout: float | None = None,
        *,
        json: TJson | None = None,
        **kwargs: Any,
    ) -> TransportRider:
        raise NotImplementedError

    @abstractmethod
    def websocket(self, url: str, **kwargs) -> TransportRider:
        raise NotImplementedError


class AbstractClientService(Service, metaclass=ABCMeta):
    id = "http.universal_client"
    supported_interface_types = {AbstractClientInterface}
