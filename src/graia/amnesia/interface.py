from typing import TYPE_CHECKING, Any, Generic, TypeVar

from graia.amnesia.status import Status

if TYPE_CHECKING:
    from graia.amnesia.service import Service


TService = TypeVar("TService", bound="Service")


class ExportInterface(Generic[TService]):
    service: TService

    def get_status(self, target: Any) -> Status:
        return self.service.get_status(target)
