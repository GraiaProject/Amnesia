from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from graia.amnesia.launch.service import Service


TService = TypeVar("TService", bound="Service")


class ExportInterface(Generic[TService]):
    service: TService
