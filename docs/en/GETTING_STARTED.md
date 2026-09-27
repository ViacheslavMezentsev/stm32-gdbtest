# Getting started

[Documentation](index.md) → Getting started · [Русский](../ru/GETTING_STARTED.md)

The main way to integrate stm32-gdbtest is a Git submodule pinned to a commit.
Python scenarios and board settings live in the consumer project. The module checks
below run from a separate checkout of the module and create build artifacts; in a
project dependency run them in a separate working copy.

## Requirements

- Hardware runs: Windows, Python ≥ 3.11, CMake ≥ 3.25, Ninja, ARM GCC with
  `arm-none-eabi-gdb-py3` (GDB with embedded Python ≥ 3.11), an SWD debugger and its
  GDB server (OpenOCD, ST-LINK GDB Server or J-Link GDB Server).
- Build, build manifest and preparation without hardware (`run --prepare-only`) also
  work on Linux; a ready environment is the CI Docker image ([checks and CI](testing.md)).
- Verified versions and boards — [status](STATUS.md). Other MCUs and versions need
  their own checks.

## Checking the module without a board

From the module root:

```powershell
python -B -m stm32_gdbtest --version
python -B -m unittest discover -s Tests/host -v
cd examples/minimal-consumer
cmake --preset debug
cmake --build --preset debug
ctest --preset offline
```

`examples/minimal-consumer` targets Windows: xPack ARM GCC 13 with GDB-Python and an
installed STM32CubeF4 V1.28.3. Paths come from `ARM_TOOLCHAIN_ROOT` and
`CUBE_F4_ROOT`, by default relative to `USERPROFILE`; local settings are not
committed. `ctest --preset offline` runs traceability, the `prepare.HW_CONSUMER_GPIO`
preparation and the offline contract check without connecting to a board.

The full CI check set (Windows and Linux, three GCC versions, three MCUs) runs with
one command in the Docker image — [checks and CI](testing.md).

## Adding the module to a project

In the consumer project:

```powershell
git submodule add https://github.com/ViacheslavMezentsev/stm32-gdbtest.git modules/stm32-gdbtest
```

Pin a verified commit or tag in the parent project's gitlink; the dependency is not
updated automatically at configure time. In CMake, after the firmware target exists:

```cmake
include(CTest)
include("${PROJECT_SOURCE_DIR}/modules/stm32-gdbtest/stm32_gdbtest/cmake/STM32GDBTest.cmake")
stm32_gdbtest_attach(firmware_target
    PROFILE_DIR "${PROJECT_SOURCE_DIR}/profiles/myboard"
    MANIFEST_INPUTS "${PROJECT_SOURCE_DIR}/profiles/myboard/firmware_FLASH.ld")
```

A profile contains `target.toml` and `Tests/` (`board/test_*.py`, `requirements.md`,
`contracts.json`). Tests are created in the project, not inside the submodule. The
local stand is selected with `STM32_GDBTEST_STAND` or `--stand`; templates are
`examples/stands/stlink.example.toml` and `Tests/firmware/stands/*.example.toml`.
Replace the serial number and, if needed, the server path, and save the file as
`*.local.toml` in the project. The CLI can be called from any directory by the
absolute path of `stm32_gdbtest/cli.py`.

Before the first hardware run, `run --prepare-only --stand <stand>` is useful: it
checks the stand, profile, manifest, contracts and image without accessing the debugger.

## Next

- [Writing tests](TEST_AUTHORING.md) — the process for people and AI agents.
- [API and CLI](API.md) — public operations and limits.
- [Maintenance](maintenance.md) and [AGENTS.md](../../AGENTS.md) — rules for changing the core.
- Profile and contract formats — examples and the `profile.py`, `contracts.py` validators.
