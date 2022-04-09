from functools import partial
from typing import Any, Dict, Optional, Type

import orjson

from .. import JSONBackend, TJson, TJsonCustomSerializer
from ..serializers import SERIALIZER_DEFAULT, SERIALIZERS


class OrjsonBackend(JSONBackend):
    def serialize(self, value: Any, *, custom_serializers: Optional[Dict[Type, TJsonCustomSerializer]] = None) -> str:
        return self.serialize_as_bytes(value, custom_serializers=custom_serializers).decode("utf-8")

    def deserialize(self, value: str) -> TJson:
        return orjson.loads(value)

    def serialize_as_bytes(
        self, value: Any, *, custom_serializers: Optional[Dict[Type, TJsonCustomSerializer]] = None
    ) -> bytes:
        return orjson.dumps(
            value,
            default=partial(
                SERIALIZER_DEFAULT, d=custom_serializers and dict(SERIALIZERS, **custom_serializers) or SERIALIZERS
            ),
        )


BACKEND_INSTANCE = OrjsonBackend()
