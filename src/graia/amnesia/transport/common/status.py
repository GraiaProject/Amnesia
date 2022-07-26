from __future__ import annotations

from statv import Stats, Statv


class ConnectionStatus(Statv):
    connected = Stats[bool]("connected", default=False)
    succeed = Stats[bool]("succeed", default=False)

    def __init__(self) -> None:
        super().__init__()

    @property
    def closed(self) -> bool:
        return not self.connected

    @property
    def available(self) -> bool:
        return self.connected
