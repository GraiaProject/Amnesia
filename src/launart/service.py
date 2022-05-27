from abc import abstractmethod
from typing import Callable, ClassVar, Dict, Set, Tuple, Type, TypeVar, Union

from launart.component import Launchable
from launart.interface import ExportInterface

TInterface = TypeVar("TInterface", bound=ExportInterface)
TCallback = TypeVar("TCallback", bound=Callable)


class Service(Launchable):
    supported_interface_types: ClassVar[
        Union[
            Set[Type[ExportInterface]],
            Dict[Type[ExportInterface], Union[int, float]],
            Tuple[
                Union[
                    Set[Type[ExportInterface]],
                    Dict[Type[ExportInterface], Union[int, float]],
                ],
                ...,
            ],
        ]
    ]

    def __init__(self) -> None:
        ...

    @abstractmethod
    def get_interface(self, interface_type: Type[TInterface]) -> TInterface:
        pass
