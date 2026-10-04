"""Per-scenario in-memory records; host-safe implementation (ТЗ API 4.9–4.10)."""

import math

from stm32_gdbtest.errors import RecordError

__all__ = ["Journal", "RecordError"]


class Journal:
    """Append snapshots; return detached copies. No export or shared state."""

    def __init__(self, *, max_records=128, max_nodes=4096, max_depth=8,
                 max_text_bytes=65536, max_integer_bits=256):
        limits = (max_records, max_nodes, max_depth, max_text_bytes, max_integer_bits)
        if any(type(n) is not int or n <= 0 for n in limits):
            raise ValueError("limits must be positive integers")
        self._limits = limits
        self._entries = []
        self._nodes = 0
        self._text_bytes = 0

    def _copy(self, value, depth, ancestors, budget):
        _, node_limit, depth_limit, text_limit, integer_bits = self._limits
        budget[0] += 1
        if budget[0] > node_limit:
            raise RecordError("limit_exceeded", "node limit exceeded", limit="nodes")
        if depth > depth_limit:
            raise RecordError("limit_exceeded", "depth limit exceeded", limit="depth")
        kind = type(value)
        if kind is str:
            # Bound allocation before UTF-8 encoding; reject lone surrogates.
            if len(value) > text_limit - budget[1]:
                raise RecordError("limit_exceeded", "text limit exceeded", limit="text_bytes")
            try:
                budget[1] += len(value.encode("utf-8"))
            except UnicodeEncodeError as exc:
                raise RecordError("invalid_text", "invalid Unicode text") from exc
            if budget[1] > text_limit:
                raise RecordError("limit_exceeded", "text limit exceeded", limit="text_bytes")
            return value
        if value is None or kind is bool:
            return value
        if kind is int:
            if value.bit_length() > integer_bits:
                raise RecordError("limit_exceeded", "integer limit exceeded", limit="integer_bits")
            return value
        if kind is float:
            if not math.isfinite(value):
                raise RecordError("non_finite", "non-finite float")
            return value
        if kind not in (list, dict):
            raise RecordError("unsupported_type", "unsupported value type")
        identity = id(value)
        if identity in ancestors:
            raise RecordError("cycle", "cyclic data")
        ancestors.add(identity)
        try:
            if kind is list:
                return [self._copy(item, depth + 1, ancestors, budget) for item in value]
            result = {}
            for key, item in value.items():
                if type(key) is not str:
                    raise RecordError("unsupported_type", "dictionary keys must be strings")
                copied_key = self._copy(key, depth + 1, ancestors, budget)
                result[copied_key] = self._copy(item, depth + 1, ancestors, budget)
            return result
        finally:
            ancestors.remove(identity)

    def record(self, name, data):
        if type(name) is not str or not name:
            raise RecordError("invalid_name", "name must be a non-empty string")
        if len(self._entries) >= self._limits[0]:
            raise RecordError("limit_exceeded", "record limit exceeded", limit="records")
        budget = [self._nodes, self._text_bytes]
        copied_name = self._copy(name, 0, set(), budget)
        snapshot = self._copy(data, 0, set(), budget)
        # Commit only after the entire value has passed validation.
        self._entries.append({"sequence": len(self._entries) + 1,
                              "name": copied_name, "data": snapshot})
        self._nodes, self._text_bytes = budget

    def records(self, name=None):
        if name is not None and (type(name) is not str or not name):
            raise RecordError("invalid_name", "filter must be None or a non-empty string")
        # Stored values have already been validated; copying cannot invoke user code.
        def clone(value):
            if type(value) is list:
                return [clone(item) for item in value]
            if type(value) is dict:
                return {key: clone(item) for key, item in value.items()}
            return value

        return [clone(entry) for entry in self._entries
                if name is None or entry["name"] == name]
