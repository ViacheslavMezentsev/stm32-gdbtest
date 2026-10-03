"""Selection/legacy checks and an actual CMake configure using production module."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from config_transport import loads
from session_bridge import prepare
from session_config import ConfigError
from test_session_config import TARGET

ROOT = Path(__file__).resolve().parents[2]
COMPILER = shutil.which("cc") or shutil.which("arm-none-eabi-gcc")


class BridgeTests(unittest.TestCase):
    def test_legacy_descriptor_is_not_augmented_or_interpreted(self):
        legacy = {"profile": "not-present.toml", "elf": "not-present.elf", "tests": "tests"}
        descriptor, capsule = prepare(legacy, image_policy="legacy-policy.toml",
                                      environ={"STM32_GDBTEST_IMAGE_POLICY": "old.toml"})
        self.assertEqual(descriptor, legacy)
        self.assertIsNone(capsule)

    def test_new_mode_api_change_and_stale_target_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target.toml").write_text(TARGET, encoding="utf-8")
            api = root / "api.toml"
            api.write_text('schema=1\n[records]\nmax_records=5', encoding="utf-8")
            config = root / "session.toml"
            config.write_text('[config]\ntarget="target.toml"\napi="api.toml"', encoding="utf-8")
            session = dict(profile=str(root / "target.toml"), session_config=str(config))
            _, first = prepare(session, environ={})
            api.write_text('schema=1\n[records]\nmax_records=9', encoding="utf-8")
            _, second = prepare(session, environ={})
            self.assertEqual(loads(first).config["api"]["records"]["max_records"], 5)
            self.assertEqual(loads(second).config["api"]["records"]["max_records"], 9)
            (root / "other.toml").write_text(TARGET, encoding="utf-8")
            config.write_text('[config]\ntarget="other.toml"', encoding="utf-8")
            with self.assertRaises(ConfigError) as caught:
                prepare(session, environ={})
            self.assertEqual(caught.exception.code, "stale_selection")

    @unittest.skipUnless(shutil.which("cmake") and shutil.which("ninja") and COMPILER,
                         "CMake/Ninja/C compiler required; exercised in Linux CI")
    def test_actual_cmake_old_new_and_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / "profile"
            (profile / "tests" / "board").mkdir(parents=True)
            (profile / "tests" / "board" / "test_fixture.py").write_text(
                'from stm32_gdbtest import case\n@case("HW_CONFIG_FIXTURE")\n'
                'def fixture(t):\n    pass\n', encoding="utf-8")
            (profile / "target.toml").write_text(TARGET, encoding="utf-8")
            (profile / "session.toml").write_text('[config]\ntarget="target.toml"', encoding="utf-8")
            (root / "main.c").write_text('int main(void) { return 0; }', encoding="utf-8")
            env = dict(os.environ)
            env.pop("STM32_GDBTEST_IMAGE_POLICY", None)
            for mode in ("old", "new", "conflict"):
                arguments = '' if mode == 'old' else 'SESSION_CONFIG "${CMAKE_SOURCE_DIR}/profile/session.toml"'
                if mode == 'conflict':
                    arguments += ' PROFILE "${CMAKE_SOURCE_DIR}/profile/target.toml"'
                cmake = '\n'.join([
                    'cmake_minimum_required(VERSION 3.25)', 'project(config_fixture C)',
                    'enable_testing()', 'add_executable(firmware main.c)',
                    f'include("{ROOT.as_posix()}/stm32_gdbtest/cmake/STM32GDBTest.cmake")',
                    f'include("{ROOT.as_posix()}/tests/api-extension/cmake/research.cmake")',
                    f'research_attach(firmware PROFILE_DIR "${{CMAKE_SOURCE_DIR}}/profile" {arguments})'])
                (root / "CMakeLists.txt").write_text(cmake, encoding="utf-8")
                build = root / mode
                # No GDB is executed; configure only needs an explicit executable path.
                result = subprocess.run(['cmake', '-G', 'Ninja', '-S', str(root), '-B', str(build),
                                         '-DCMAKE_C_COMPILER='+COMPILER,
                                         '-DCMAKE_SYSTEM_NAME=Generic',
                                         '-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY',
                                         '-DSTM32_GDBTEST_GDB='+sys.executable],
                                        capture_output=True, text=True, env=env)
                if mode == 'conflict':
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('SESSION_CONFIG conflicts with PROFILE', result.stderr)
                    continue
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                standard = json.loads((build/'hwtest/session.json').read_text())
                self.assertEqual(set(standard), {'elf','gdb','tests','root','out','stand','profile','build_manifest'})
                if mode == 'new':
                    extra = json.loads((build/'hwtest/research-session.json').read_text())
                    _, capsule = prepare({**standard, **extra}, environ={})
                    self.assertEqual(loads(capsule).config['target']['mcu'], 'STM32F411CEU6')
                else:
                    self.assertFalse((build/'hwtest/research-session.json').exists())


if __name__ == '__main__':
    unittest.main()
