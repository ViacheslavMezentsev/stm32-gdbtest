#!/bin/sh
set -eu

# Only the selected GCC and CMake are put on PATH; unsupported versions fail early.
selection=$(python3 - <<'PY'
import json, os, sys
from pathlib import Path
lock = json.loads(Path('/opt/stm32-gdbtest-ci/dependencies.lock.json').read_text())
gcc = os.environ.get('GCC_VERSION', lock['default_gcc'])
cmake = os.environ.get('CMAKE_VERSION', lock['default_cmake'])
if gcc not in lock['gcc_versions'] or cmake not in lock['cmake_versions']:
    sys.exit(f'Unsupported GCC_VERSION={gcc} or CMAKE_VERSION={cmake}; see ci/dependencies.lock.json')
print(gcc, cmake)
PY
)
set -- $selection -- "$@"
GCC_VERSION=$1
CMAKE_VERSION=$2
shift 3
ARM_TOOLCHAIN_ROOT=/opt/xpack-arm-none-eabi-gcc-${GCC_VERSION}
export GCC_VERSION CMAKE_VERSION ARM_TOOLCHAIN_ROOT
export PATH="/opt/cmake-${CMAKE_VERSION}/bin:${ARM_TOOLCHAIN_ROOT}/bin:${PATH}"
exec "$@"
