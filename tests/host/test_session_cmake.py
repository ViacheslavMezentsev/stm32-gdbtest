"""Selection/legacy checks and an actual CMake configure using production module."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from stm32_gdbtest.configuration import capture
from test_session_config import TARGET

ROOT = Path(__file__).resolve().parents[2]
COMPILER = shutil.which("cc") or shutil.which("arm-none-eabi-gcc")


class CMakeSessionTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("cmake") and shutil.which("ninja") and COMPILER,
                         "CMake/Ninja/C compiler required; exercised in Linux CI")
    def test_minimal_consumer_resolves_relative_module_for_ctest(self):
        # A relative path requires both trees to be on the same Windows drive.
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory) / "consumer"
            shutil.copytree(ROOT / "examples/minimal-consumer", root,
                            ignore=shutil.ignore_patterns("build", "__pycache__"))
            build = root / "build"
            result = subprocess.run([
                "cmake", "-G", "Ninja", "-S", str(root), "-B", str(build),
                "-DCMAKE_C_COMPILER=" + COMPILER, "-DCMAKE_SYSTEM_NAME=Generic",
                "-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY",
                "-DSTM32_GDBTEST_GDB=" + sys.executable,
                "-DSTM32_GDBTEST_SOURCE_DIR:PATH=" + Path(os.path.relpath(ROOT, root)).as_posix()
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            listing = subprocess.run(["ctest", "--test-dir", str(build), "--show-only=json-v1"],
                                     capture_output=True, text=True, check=True)
            command = next(test["command"] for test in json.loads(listing.stdout)["tests"]
                           if test["name"] == "host.consumer_offline")
            self.assertTrue(Path(command[-1]).is_absolute())
            self.assertEqual(Path(command[-1]).resolve(), ROOT.resolve())

    @unittest.skipUnless(shutil.which("cmake") and shutil.which("ninja") and COMPILER,
                         "CMake/Ninja/C compiler required; exercised in Linux CI")
    def test_actual_cmake_old_new_and_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / "profile"
            (profile / "tests" / "board").mkdir(parents=True)
            (profile / "tests" / "board" / "test_fixture.py").write_text(
                'from stm32_gdbtest import test\n@test("HW_CONFIG_FIXTURE")\n'
                'def fixture(t):\n    pass\n', encoding="utf-8")
            (profile / "target.toml").write_text(TARGET, encoding="utf-8")
            (profile / "session.toml").write_text('[config]\ntarget="target.toml"', encoding="utf-8")
            common = root / "common"
            (common / "board").mkdir(parents=True)
            (common / "board" / "test_common.py").write_text(
                'from stm32_gdbtest import case\n@case("HW_COMMON_FIXTURE")\n'
                'def common(t):\n    pass\n', encoding="utf-8")
            (common / "requirements.md").write_text("## HW_COMMON_FIXTURE\nShared.\n", encoding="utf-8")
            (root / "main.c").write_text('int main(void) { return 0; }', encoding="utf-8")
            env = dict(os.environ)
            env.pop("STM32_GDBTEST_IMAGE_POLICY", None)
            for mode in ("old", "new", "conflict", "extra"):
                arguments = '' if mode == 'old' else 'SESSION_CONFIG "${CMAKE_SOURCE_DIR}/profile/session.toml"'
                if mode == 'conflict':
                    arguments += ' PROFILE "${CMAKE_SOURCE_DIR}/profile/target.toml"'
                if mode == 'extra':
                    arguments = 'TEST_DIRS "${CMAKE_SOURCE_DIR}/common"'
                cmake = '\n'.join([
                    'cmake_minimum_required(VERSION 3.25)', 'project(config_fixture C)',
                    'enable_testing()', 'add_executable(firmware main.c)',
                    f'include("{ROOT.as_posix()}/stm32_gdbtest/cmake/STM32GDBTest.cmake")',
                    f'stm32_gdbtest_attach(firmware PROFILE_DIR "${{CMAKE_SOURCE_DIR}}/profile" {arguments})'])
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
                expected = {'elf','gdb','tests','root','out','stand','profile','build_manifest','test_dirs'}
                self.assertEqual(set(standard), expected | ({'session_config'} if mode == 'new' else set()))
                # ТЗ 5.13.2: extra scenario directories follow the profile one in the session and in CTest.
                # Compared resolved: on Windows the temporary directory may come as an 8.3 short name.
                extra = [(common / "board").resolve()] if mode == 'extra' else []
                self.assertEqual([Path(path).resolve() for path in standard['test_dirs']], extra)
                registered = (build / 'hwtest/tests.cmake').read_text()
                self.assertIn('HW_CONFIG_FIXTURE', registered)
                self.assertEqual('HW_COMMON_FIXTURE' in registered, mode == 'extra')
                self.assertEqual(capture(standard, environ={}).config['target']['mcu'], 'STM32F411CEU6')


if __name__ == '__main__':
    unittest.main()
