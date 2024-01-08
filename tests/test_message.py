from graia.amnesia.message import MessageChain
from graia.amnesia.message.element import Text, Unknown


def test_init():
    assert MessageChain(["123", "456"]).merge(copy=False) == MessageChain("123456")


def test_bool():
    assert not MessageChain([])
    assert not MessageChain("")


def test_strip():
    msg = MessageChain([Text("    123"), Unknown("at", {"id": 1})])

    assert msg.lstrip() == MessageChain([Text("123"), Unknown("at", {"id": 1})])
    assert msg.rstrip(Unknown) == MessageChain("    123")
    assert msg.strip(" ", Unknown) == MessageChain("123")
    assert msg.strip(Text, Unknown).empty()


def test_replace():
    msg = MessageChain([Text("    123"), Unknown("at", {"id": 1})])

    assert msg.replace([Text("123")], [Text("456")]) == MessageChain([Text("    456"), Unknown("at", {"id": 1})])


def test_remove():
    msg = MessageChain([Text("123"), Unknown("at", {"id": 1}), Text("456")])

    assert msg.removeprefix("123") == MessageChain([Unknown("at", {"id": 1}), Text("456")])
    assert msg.removesuffix("456") == MessageChain([Text("123"), Unknown("at", {"id": 1})])
