from copy import copy
from dataclasses import dataclass


@dataclass
class Status:
    available: bool
    stage: str = "unknown"

    def frame(self):
        return copy(self)
