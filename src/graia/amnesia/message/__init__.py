from __future__ import annotations

from collections.abc import Iterable, Iterator
from copy import deepcopy
from typing import TYPE_CHECKING, ClassVar, TypeVar

from typing_extensions import Self

from .element import Element, Text


class MessageChain:
    """即 "消息链", 被用于承载整个消息内容的数据结构, 包含有一有序列表, 包含有继承了 Element 的各式类实例.

    - 你可以通过实例化 `MessageChain` 创建一个消息链

    - `MessageChain.has` 方法可用于判断特定的元素类型是否存在于消息链中

    - `MessageChain.get` 方法可以获取消息链中的所有特定类型的元素

    - `MessageChain.get_first` 方法可以获取消息链中的第 1 个特定类型的元素

    - `MessageChain.get_one` 方法可以获取消息链中的第 index + 1 个特定类型的元素

    - 使用 `str` 函数可以获取到字符串形式表示的消息

    - 使用 `MessageChain(...).join` 方法可以拼接多个消息链并插入指定内容

    - `MessageChain.merge` 方法可以将消息链中相邻的 Text 元素合并为一个 Text 元素.

    - `MessageChain.startswith` 方法可以判断消息链是否以指定的文本开头

    - `MessageChain.endswith` 方法可以判断消息链是否以指定的文本结尾

    - `MessageChain.include` 方法可以创建只包含指定元素类型的消息链

    - `MessageChain.exclude` 方法可以创建排除指定元素类型的消息链

    - `MessageChain.split` 方法可以用指定文本将消息链拆分为多个

    - `MessageChain.append` 方法可以将指定的元素添加到消息链的末尾

    - `MessageChain.extend` 方法可以将指定的序列/消息链添加到消息链的末尾

    - `MessageChain.only` 可以检查是否只包含指定元素

    - `MessageChain.index` 可以获取指定元素在消息链中的索引

    - `MessageChain.count` 可以获取消息链中指定元素的数量

    - `MessageChain.copy` 可以获取消息链的拷贝

    """

    __text_element_class__: ClassVar[type[Text]] = Text
    content: list[Element]

    def __init__(self, elements: list[Element]):
        """从传入的序列(可以是元组 tuple, 也可以是列表 list) 创建消息链.
        Args:
            elements (list[T]): 包含且仅包含消息元素的序列
        Returns:
            MessageChain: 以传入的序列作为所承载消息的消息链
        """
        self.content = elements

    def has(self, element_class: type[Element]) -> bool:
        """判断消息链中是否含有特定类型的消息元素
        Args:
            element_class (T): 需要判断的消息元素的类型, 例如 "Text", "Notice", "Image" 等.
        Returns:
            bool: 判断结果
        """
        return element_class in [type(i) for i in self.content]

    if TYPE_CHECKING:
        E = TypeVar("E", bound=Element)

    def get(self, element_class: "type[E]") -> "list[E]":
        """获取消息链中所有特定类型的消息元素
        Args:
            element_class (T): 指定的消息元素的类型, 例如 "Text", "Notice", "Image" 等.
        Returns:
            list[T]: 获取到的符合要求的所有消息元素; 另: 可能是空列表([]).
        """
        return [i for i in self.content if isinstance(i, element_class)]

    def get_one(self, element_class: "type[E]", index: int) -> "E":
        """获取消息链中第 index + 1 个特定类型的消息元素
        Args:
            element_class (type[Element]): 指定的消息元素的类型, 例如 "Text", "Notice", "Image" 等.
            index (int): 索引, 从 0 开始数
        Returns:
            T: 消息链第 index + 1 个特定类型的消息元素
        """
        return self.get(element_class)[index]

    def get_first(self, element_class: "type[E]") -> "E":
        """获取消息链中第 1 个特定类型的消息元素
        Args:
            element_class (type[Element]): 指定的消息元素的类型, 例如 "Text", "Notice", "Image" 等.
        Returns:
            T: 消息链第 1 个特定类型的消息元素
        """
        return self.get(element_class)[0]

    def __str__(self) -> str:
        """获取以字符串形式表示的消息链, 且趋于通常你见到的样子.
        Returns:
            str: 以字符串形式表示的消息链
        """
        return "".join(str(i) for i in self.content)

    def join(self, *chains: Self | Iterable[Self]) -> Self:
        """将多个消息链连接起来, 并在其中插入自身.

        Args:
            *chains (Iterable[MessageChain]): 要连接的消息链.

        Returns:
            MessageChain: 连接后的消息链, 已对文本进行合并.
        """
        result: list[Element] = []
        list_chains: list[MessageChain] = []
        for chain in chains:
            if isinstance(chain, MessageChain):
                list_chains.append(chain)
            else:
                list_chains.extend(chain)

        for chain in list_chains:
            if chain is not list_chains[0]:
                result.extend(deepcopy(self.content))
            result.extend(deepcopy(chain.content))
        return self.__class__(result).merge()

    __contains__ = has

    def __getitem__(self, item: type[Element] | slice):
        if isinstance(item, slice):
            return self.__class__(self.content[item])
        elif issubclass(item, Element):
            return self.get(item)
        else:
            raise NotImplementedError("{0} is not allowed for item getting".format(type(item)))

    def merge(self) -> Self:
        """合并相邻的 Text 项, 并返回一个新的消息链实例
        Returns:
            MessageChain: 得到的新的消息链实例, 里面不应存在有任何的相邻的 Text 元素.
        """

        result = []

        texts = []
        for i in self.content:
            if not isinstance(i, Text):
                if texts:
                    result.append(self.__class__.__text_element_class__("".join(texts)))
                    texts.clear()  # 清空缓存
                result.append(i)
            else:
                texts.append(i.text)
        if texts:
            result.append(self.__class__.__text_element_class__("".join(texts)))
            texts.clear()  # 清空缓存
        return self.__class__(result)

    def exclude(self, *types: type[Element]) -> Self:
        """将除了在给出的消息元素类型中符合的消息元素重新包装为一个新的消息链
        Args:
            *types (type[Element]): 将排除在外的消息元素类型
        Returns:
            MessageChain: 返回的消息链中不包含参数中给出的消息元素类型
        """
        return self.__class__([i for i in self.content if not isinstance(i, types)])

    def include(self, *types: type[Element]) -> Self:
        """将只在给出的消息元素类型中符合的消息元素重新包装为一个新的消息链
        Args:
            *types (type[Element]): 将只包含在内的消息元素类型
        Returns:
            MessageChain: 返回的消息链中只包含参数中给出的消息元素类型
        """
        return self.__class__([i for i in self.content if isinstance(i, types)])

    def split(self, pattern: str = " ", raw_string: bool = False) -> list[Self]:
        """和 `str.split` 差不多, 提供一个字符串, 然后返回分割结果.

        Args:
            pattern (str): 分隔符. 默认为单个空格.
            raw_string (bool): 是否要包含 "空" 的文本元素.

        Returns:
            list[Self]: 分割结果, 行为和 `str.split` 差不多.
        """

        result: list[Self] = []
        tmp = []
        for element in self.content:
            if isinstance(element, Text):
                split_result = element.text.split(pattern)
                for index, split_str in enumerate(split_result):
                    if tmp and index > 0:
                        result.append(self.__class__(tmp))
                        tmp = []
                    if split_str or raw_string:
                        tmp.append(self.__class__.__text_element_class__(split_str))
            else:
                tmp.append(element)
        if tmp:
            result.append(self.__class__(tmp))
            tmp = []
        return result

    def __repr__(self) -> str:
        return f"MessageChain({repr(self.content)})"

    def __iter__(self) -> Iterator[Element]:
        yield from self.content

    def startswith(self, string: str) -> bool:
        """判断消息链是否以给出的字符串开头

        Args:
            string (str): 字符串

        Returns:
            bool: 是否以给出的字符串开头
        """

        if not self.content or not isinstance(self.content[0], Text):
            return False
        return self.content[0].text.startswith(string)

    def endswith(self, string: str) -> bool:
        """判断消息链是否以给出的字符串结尾

        Args:
            string (str): 字符串

        Returns:
            bool: 是否以给出的字符串结尾
        """

        if not self.content or not isinstance(self.content[-1], Text):
            return False
        return self.content[-1].text.endswith(string)

    def only(self, *element_classes: type[Element]) -> bool:
        """判断消息链中是否只含有特定类型元素.

        Args:
            *element_classes (type[Element]): 元素类型

        Returns:
            bool: 判断结果
        """
        return all(isinstance(i, element_classes) for i in self.content)

    def append(self, element: Element | str, copy: bool = False) -> Self:
        """
        向消息链最后追加单个元素

        Args:
            element (Element): 要添加的元素
            copy (bool): 是否要在副本上修改.

        Returns:
            MessageChain: copy = True 时返回副本, 否则返回自己的引用.
        """
        chain_ref = self.copy() if copy else self
        if isinstance(element, str):
            element = self.__class__.__text_element_class__(element)
        chain_ref.content.append(element)
        return chain_ref

    def extend(
        self,
        *content: Self | Element | list[Element | str],
        copy: bool = False,
    ) -> Self:
        """
        向消息链最后添加元素/元素列表/消息链

        Args:
            *content (MessageChain | Element | list[Element | str]): 要添加的元素/元素容器.
            copy (bool): 是否要在副本上修改.

        Returns:
            MessageChain: copy = True 时返回副本, 否则返回自己的引用.
        """
        result = []
        for i in content:
            if isinstance(i, Element):
                result.append(i)
            elif isinstance(i, str):
                result.append(self.__class__.__text_element_class__(i))
            elif isinstance(i, MessageChain):
                result.extend(i.content)
            else:
                for e in i:
                    if isinstance(e, str):
                        result.append(self.__class__.__text_element_class__(e))
                    else:
                        result.append(e)
        if copy:
            return self.__class__(deepcopy(self.content) + result)
        self.content.extend(result)
        return self

    def copy(self) -> Self:
        """
        拷贝本消息链.

        Returns:
            MessageChain: 拷贝的副本.
        """
        return self.__class__(deepcopy(self.content))

    def index(self, element_type: type[Element]) -> int | None:
        """
        寻找第一个特定类型的元素, 并返回其下标.

        Args:
            element_type (type[Element]): 元素或元素类型

        Returns:
            int | None: 元素下标, 若未找到则为 None.

        """
        return next((i for i, e in enumerate(self.content) if isinstance(e, element_type)), None)

    def count(self, element: type[Element] | Element) -> int:
        """
        统计共有多少个指定的元素.

        Args:
            element (type[Element] | Element): 元素或元素类型

        Returns:
            int: 元素数量
        """
        if isinstance(element, Element):
            return sum(i == element for i in self.content)
        return sum(isinstance(i, element) for i in self.content)
