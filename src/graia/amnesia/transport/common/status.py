from copy import copy
from typing import Optional

from graia.amnesia.status.standalone import AbstractStandaloneStatus


class ConnectionStatus(AbstractStandaloneStatus):
    id: str = ""  # avoid abstract check
    connected: bool = False
    succeed: bool = False

    def __init__(self, id: str) -> None:
        self.id = id

    def frame(self):
        instance = copy(self)
        instance._waiter = None
        return instance

    @property
    def closed(self) -> bool:
        return not self.connected

    @property
    def available(self) -> bool:
        return self.connected

    def update(self, connected: Optional[bool] = None, succeed: Optional[bool] = None):
        past = self.frame()
        if connected is not None:
            self.connected = connected
        if succeed is not None:
            self.succeed = succeed
        if self._waiter:
            self._waiter.set_result((past, self))
