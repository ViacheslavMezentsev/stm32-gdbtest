"""Frame chain walking: depth, limit, completeness and broken accessors."""
import importlib
import sys
import types
import unittest
from unittest.mock import Mock, patch

from stm32_gdbtest import ApiError
from stm32_gdbtest.configuration import DEFAULTS, FRAMES_LIMIT, Configuration, freeze

NORMAL_FRAME, SIGTRAMP_FRAME = 0, 2


class FakeError(Exception):
    pass


class BrokenPc:
    def pc(self):
        raise FakeError("pc unavailable")


class FakeFrame:
    def __init__(self, name, pc, older=None, kind=NORMAL_FRAME, broken_pc=False):
        self._name = name
        self._pc = pc
        self._older = older
        self._kind = kind
        self._broken_pc = broken_pc

    def is_valid(self):
        return True

    def name(self):
        return self._name

    def pc(self):
        if self._broken_pc:
            raise FakeError("pc unavailable")
        return self._pc

    def type(self):
        return self._kind

    def older(self):
        return self._older


class FramesTests(unittest.TestCase):
    def setUp(self):
        self.chain = FakeFrame("app_loop", 0x8000100, FakeFrame("main", 0x8000200))
        self.gdb = types.SimpleNamespace(
            error=FakeError,
            newest_frame=lambda: self.chain,
            NORMAL_FRAME=NORMAL_FRAME,
            SIGTRAMP_FRAME=SIGTRAMP_FRAME,
            parse_and_eval=lambda expression: types.SimpleNamespace(
                is_optimized_out=False, fetch_lazy=lambda: None, __int__=lambda self: 0),
            events=types.SimpleNamespace(stop=Mock()),
        )

    def target(self, api=None):
        import builtins
        real_import = builtins.__import__

        def importing_gdb(name, *arguments, **options):
            if name == "gdb":
                return self.gdb
            return real_import(name, *arguments, **options)

        saved = {name: sys.modules.pop(name, None)
                 for name in ("stm32_gdbtest.target", "stm32_gdbtest.values")}
        with patch.object(builtins, "__import__", side_effect=importing_gdb):
            module = importlib.import_module("stm32_gdbtest.target")
        for name, previous in saved.items():
            sys.modules.pop(name, None)
            if previous is not None:
                sys.modules[name] = previous
        settings = dict(schema=1, records=dict(DEFAULTS))
        if api:
            settings.update(api)
        configuration = Configuration(freeze(dict(target={}, image=None, api=settings)),
                                      freeze(dict(target=None, api=None, image=None)), None, {})
        return module.Target({"checks": []}, {"breakpoint_limit": 4, "fault_handlers": []},
                             configuration)

    def test_frames_walk_from_the_innermost(self):
        target = self.target()
        result = target.frames()
        self.assertEqual(result["operation"], "frames")
        self.assertEqual([entry["name"] for entry in result["frames"]], ["app_loop", "main"])
        self.assertEqual([entry["depth"] for entry in result["frames"]], [0, 1])
        self.assertEqual(result["frames"][0]["pc"], 0x8000100)
        self.assertEqual(result["frames"][0]["method"], "normal")
        self.assertEqual(result["count"], 2)
        self.assertTrue(result["complete"])

    def test_frames_stop_at_the_limit(self):
        target = self.target()
        result = target.frames(limit=1)
        self.assertEqual(len(result["frames"]), 1)
        self.assertEqual(result["limit"], 1)
        self.assertFalse(result["complete"])

    def test_frames_use_the_configured_limit(self):
        target = self.target(api=dict(frames=dict(limit=8)))
        result = target.frames()
        self.assertEqual(result["limit"], 8)
        target_default = self.target()
        self.assertEqual(target_default.frames()["limit"], FRAMES_LIMIT)

    def test_frames_reject_an_invalid_limit(self):
        target = self.target()
        for limit in (0, -1, "16", 1.5):
            with self.subTest(limit=limit):
                with self.assertRaises(ApiError) as caught:
                    target.frames(limit=limit)
                self.assertEqual(caught.exception.code, "invalid_limit")
        configured = self.target(api=dict(frames=dict(limit="16")))
        with self.assertRaises(ApiError) as caught:
            configured.frames()
        self.assertEqual(caught.exception.code, "invalid_limit")

    def test_frames_report_a_missing_frame(self):
        target = self.target()
        self.gdb.newest_frame = lambda: None
        with self.assertRaises(ApiError) as caught:
            target.frames()
        self.assertEqual(caught.exception.code, "no_frame")

    def test_frames_survive_a_broken_pc(self):
        target = self.target()
        self.chain = FakeFrame("app_loop", 0, FakeFrame("main", 0x8000200), broken_pc=True)
        result = target.frames()
        self.assertIsNone(result["frames"][0]["pc"])
        self.assertEqual(result["frames"][1]["pc"], 0x8000200)

    def test_frames_mark_a_signal_frame(self):
        target = self.target()
        self.chain = FakeFrame("<signal handler called>", 0x8000300, kind=SIGTRAMP_FRAME)
        self.assertEqual(target.frames()["frames"][0]["method"], "signal")


if __name__ == "__main__":
    unittest.main()
