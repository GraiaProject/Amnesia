from typing import Any, Optional


class Element:
    def __str__(self) -> str:
        return ""


class Text(Element):
    text: str
    style: Optional[str]

    def __init__(self, text: str, style: Optional[str] = None) -> None:
        """实例化一个 Text 消息元素, 用于承载消息中的文字.

        Args:
            text (str): 元素所包含的文字
            style (Optional[str]): 默认为空, 文字的样式
        """
        self.text = text
        self.style = style

    def __str__(self) -> str:
        return self.text


class Unknown(Element):
    type: str
    raw_data: Any

    def __init__(self, type: str, raw_data: Any) -> None:
        self.type = type
        self.raw_data = raw_data

    def asDisplay(self) -> str:
        return f"[$Unknown:type={self.type}]"
