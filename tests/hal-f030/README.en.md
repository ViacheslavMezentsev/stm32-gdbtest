# NUCLEO-F030R8 HAL regression

[Русский](README.md) · [Plan and acceptance](../../docs/en/F030_HAL_REGRESSION.md)

Standalone stm32-gdbtest fixture for HAL macros, handles/callbacks and force_return.
Preserves the original17 F030 scenarios; the CMSIS fixture stays in tests/firmware.
This is an offline migration, not a new HW PASS.

Requires CMake3.25+, Ninja, Python3.11+, xPack ARM GCC13 with GDB-Python and
STM32CubeF0 V1.11.6. Set ARM_TOOLCHAIN_ROOT and STM32CUBE_REPOSITORY in the
environment or CMake cache. CubeMX and stm32-cmake-yml are not needed to build.
From this directory:

```sh
cmake --preset debug
cmake --build --preset debug
ctest --preset offline
```

Expect19 host tests:17 prepare, traceability and fixture inventory/imports/hashes.
Unfiltered CTest runs hardware tests; do not run before selecting a stand.
Build/results live in build/debug. No private stand is included.
Explicit flags: -Og -g3 -fno-lto; this is a separate firmware variant.
Do not extend PASS to Release/LTO/GCC14/15 or other backends.

Provenance: [source.json](provenance/source.json) records the source commit, paths
and before/after SHA256 with CRLF→LF normalization. Firmware is unchanged;
Python imports are local and TECH references added. The source IOC is provenance
only; automatic regeneration in this directory is not configured.

Licensing: [application MIT](LICENSE) does not override ST rights. Original
copyright/license notices in Core/startup/linker are retained, including the
CubeMX AS-IS fallback. [CMSIS Device license](licenses/cmsis-device.txt) and
[Cube component table](licenses/cube-components.md) are retained; external
HAL/CMSIS libraries retain their own licenses. Format checking covers owned
src/app.h and src/*.cpp using src/.clang-format; Core and preserved platform.c
are excluded from formatting.
