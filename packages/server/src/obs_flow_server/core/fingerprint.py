import hashlib
import msgspec


class BasePayload(msgspec.Struct, omit_defaults=True):
    def _to_canonical_json(self) -> bytes:
        # Sort any list fields to ensure deterministic output before encoding
        for field in self.__struct_fields__:
            val = getattr(self, field)
            if isinstance(val, list):
                setattr(self, field, sorted(val))

        # msgspec serializes fields in the order they are defined.
        # Subclasses MUST define fields alphabetically to ensure lexicographical sorting of keys.
        return msgspec.json.encode(self)

    def compute_fingerprint(self) -> str:
        return hashlib.sha256(self._to_canonical_json()).hexdigest()
