import re
from typing import ClassVar, Dict, List, Sequence, Type, Union

from graia.amnesia.message import MessageChain
from graia.amnesia.message.element import Element


class Formatter:

    format_string: str
    __message_chain_class__: ClassVar[Type[MessageChain]] = MessageChain

    def __init__(self, format_string: str) -> None:
        self.format_string = format_string

    @classmethod
    def ensure_element(cls, obj: Union[str, Element]) -> Element:
        return cls.__message_chain_class__.__text_element_class__(obj) if isinstance(obj, str) else obj

    @classmethod
    def extract_chain(cls, obj: Union[Element, MessageChain, str, Sequence[Element]]) -> List[Element]:
        if isinstance(obj, MessageChain):
            return obj.content
        if isinstance(obj, str):
            obj = cls.ensure_element(obj)
        if isinstance(obj, Element):
            return [obj]
        if isinstance(obj, Sequence):
            return list(obj)

    def format(
        self, *o_args: Union[Element, MessageChain, str], **o_kwargs: Union[Element, MessageChain, str]
    ) -> MessageChain:
        args: List[List[Element]] = [self.extract_chain(e) for e in o_args]
        kwargs: Dict[str, List[Element]] = {k: self.extract_chain(e) for k, e in o_kwargs.items()}

        args_mapping: Dict[str, List[Element]] = {f"\x02{index}\x02": chain for index, chain in enumerate(args)}
        kwargs_mapping: Dict[str, List[Element]] = {f"\x03{key}\x03": chain for key, chain in kwargs.items()}

        result = self.format_string.format(*args_mapping, **{k: f"\x03{k}\x03" for k in kwargs})

        chain_list: List[Element] = []

        for i in re.split("([\x02\x03][\\d\\w]+[\x02\x03])", result):
            if match := re.fullmatch("(?P<header>[\x02\x03])(?P<content>\\w+)(?P=header)", i):
                header = match["header"]
                full: str = match[0]
                if header == "\x02":  # from args
                    chain_list.extend(args_mapping[full])
                else:  # \x03, from kwargs
                    chain_list.extend(kwargs_mapping[full])
            else:
                chain_list.append(self.ensure_element(i))
        return MessageChain(chain_list).merge()
