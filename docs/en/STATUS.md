# stm32-gdbtest status

[Documentation](index.md) → Status · [Русский](../ru/STATUS.md)

Snapshot: 2026-09-28. Development version **0.1.0.dev0**, `API_VERSION = 1`; no
release tags yet. The main delivery is a pinned Git submodule; there is no pip package
or separate executable yet. This page describes the verified scope, not a change log;
history is in the [CHANGELOG](../../CHANGELOG.en.md).

## Checks

| Area | Verified scope |
| --- | --- |
| Host tests | 79 unittests without an MCU; on Linux 4 Windows lock tests are skipped, on Windows 5 Linux tests (`flock` lock, process groups) |
| CI (GitHub Actions, Docker) | Docs, format, host on Windows and Linux; F030R8/F103C8/F411CE CI firmware with GCC 13.3.1, 14.2.1, 15.2.1 and CMake 3.28.3: build manifest, `prepare`, full image, 10 negative contracts, load section alignment, empty RAM section; the Linux stand environment in `ubuntu:20.04` on x86_64 and aarch64 ([checks and CI](testing.md)) |
| CI firmware on hardware | 4 stands × 10/10 steps at commit `fbc103d` (section below) |
| Linux stand without hardware | Ubuntu 20.04 x86_64 (glibc 2.31, Python 3.8, git 2.25) in a container: environment installation, 79 host tests, `doctor`, `build` and `prepare` of the CI firmware; the hardware path without a debugger — lock, OpenOCD start, ERROR "exited before ready", processes stopped |
| Remote GDB server on hardware | Runner and GDB on Windows 10, GDB servers on Orange Pi 5 over SSH: F411CE / OpenOCD, F103C8 / J-Link CE, F030R8 / J-Link STLink — 10/10 each (`run_hw.py`) |
| Remote GDB server without hardware | SSH loopback (OpenSSH, key, `known_hosts`) and a fake J-Link server: port forwarding, GDB connecting through the tunnel, recovery, stopping the server and returning its log, refusal on a busy stand host lock, cleanup after a broken session |
| Linux stand on hardware | Orange Pi 5, Ubuntu 20.04 aarch64, `run_hw.py`: F411CE / ST-Link V2J43M28 / xPack OpenOCD 0.12.0-7 — 10/10; F103C8 / J-Link CE V9 / J-Link GDB Server 8.32 arm64 — 10/10; F030R8 / J-Link STLink V21 / J-Link GDB Server 9.80 arm64 — 10/10 after confirming the J-Link STLink terms window in a graphical session; without it the connection waits about 10 s, the first run gave 2/10 ([Linux stand](LINUX_STAND.md)) |
| ELF/HAL preflight | Positive case and 11 negative variants on F103C8/F401CC/F411CE ELF files of the stand project |
| Stand project, F411CE / ST-Link / OpenOCD | 24/24 CTest (22 HW + 2 host) after the module split |
| Stand project, F103C8 / J-Link | 24/24 CTest (22 HW + 2 host) |
| Stand project, F030R8 / J-Link STLink | 17/17 HW |
| Stand project, F429ZI / ST-Link/V2 | 22/22 HW through OpenOCD and the ST server with module `b76d909`; occasional USB failures in long series ([protocol](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/F429_SERVER_STABILITY.md), Russian) |
| Independent F411 consumer | Build and offline, hardware scenario, verify-only, timeout/recovery and restoring the main firmware |
| F401CC / ST-Link, ST server on F1/F4 | Earlier hardware checks; new macro scenarios were not repeated after the module split |

Scenario counts refer to the consumer application, not to a universal module suite
and not to code coverage. Documentation changes are not new hardware runs. Protocols,
ELF hashes and limits of the stand project (Russian):
[stand status](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/STATUS.md),
[consumer check](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/CONSUMER_VALIDATION.md),
[methods and experiments](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/STM32_TESTING_METHODS.md).

Verified tools: xPack ARM GCC 13.3.1-1.1, GDB 14.2.90 with embedded Python 3.11.4,
OpenOCD 0.12.0, ST-LINK GDB Server 7.14.0 (CubeCLT 1.22.0), J-Link 8.32; CubeF0 1.11.6,
CubeF1 1.8.7, CubeF4 1.28.3. CI also builds with GCC 14.2.1 and 15.2.1 (GDB 15.2.90
and 16.3.90 with Python 3.12 and 3.13). A GCC version does not guarantee the GDB Python
API contents; a matching HAL version does not prove matching behaviour.

## Hardware check of the CI firmware, 2026-09-28

Commit `fbc103d`, `Tests/firmware/run_hw.py`, xPack GCC 13.3.1-1.1. Every stand passed
all 10 steps: build and CTest host, preparation with the stand, programming and a
repeat without programming, strict identity, a 16 KiB full image with an 0xA5 tail,
the expected verify-only ERROR without programming, 0xFF restore, a 0.2 s timeout with
recovery through a separate GDB client and a PASS afterwards.

| Board / MCU | Debugger / backend | Result |
| --- | --- | --- |
| NUCLEO-F030R8 / STM32F030R8 | J-Link STLink (V21), J-Link GDB Server 8.32 | 10/10 |
| WeAct BluePill-Plus / STM32F103C8 | J-Link CE (V9), J-Link GDB Server 8.32 | 10/10; warning: factory Flash size 128 KiB against a 64 KiB profile |
| WeAct BlackPill / STM32F411CE | ST-Link V2J43M28, OpenOCD 0.12.0 | 10/10 |
| WeAct BlackPill / STM32F411CE | ST-Link V2J43M28, ST-LINK GDB Server 7.14.0 | 10/10, including full mode through the ST server |

The first F030R8 run found a HardFault in `Reset_Handler`: the `.data` load address
was unaligned, and Cortex-M0 does not allow unaligned word reads. The linker scripts
were fixed and CI checks the alignment — an example of a run-time defect that checks
without hardware cannot see. After `fbc103d` the BIN is built from the selected
sections only; before the release the hardware check is repeated on the final commit
(item 8.19 of the [specification](../TECHNICAL_SPECIFICATION.md)). The
stm32-hwtest-blackpill suite was not repeated on these commits.

## Implementation limits

- Hardware runs on Windows and Linux x86_64/aarch64 (glibc ≥ 2.31); on Linux they are
  checked on Orange Pi 5 (aarch64) with OpenOCD, J-Link CE and J-Link STLink; Linux x86_64 was not
  checked on hardware. The GDB server runs on the runner's
  computer or on a Linux stand host over SSH (`[remote]`); the remote mode is checked from
  Windows to Orange Pi 5; a broken session only with SSH loopback and a fake server. Ninja, one firmware target and one MCU and debugger per run.
- ST-LINK GDB Server is unavailable on Linux aarch64 (ST does not release it for arm64).
- The build manifest uses Cube and CMSIS metadata; a universal build system and an
  arbitrary toolchain are not claimed.
- J-Link mapping verified for STM32F103C8T6 → STM32F103C8 and STM32F030R8T6 → STM32F030R8.
- The target schema has mandatory OpenOCD fields. H503 is not supported.
- `-g3` is needed for macros in the debug information but does not keep unused
  functions. Contracts check the selected symbols, types and expansions, not the whole
  HAL semantics.
- Halt changes MCU behaviour; current, exact timing and physical signals need
  external methods.
- Cross-project locking works within one Windows session or one Linux host for
  participating runners; vendor tools are not controlled by it, and a release after a
  crash does not guarantee that the child server exited. Windows and WSL locks are
  independent.
- Results are PASS, FAIL, ERROR; there is no automatic SKIP, multi-node or power
  control with reconnect. Recovery is an attempt, not a guarantee after a physical
  loss of the link or power.

The consumer example contains its own firmware: its full CTest includes a hardware
test and may replace Flash, while `ctest --preset offline` does not connect to a board.

## Next steps

Before v0.1.0: runs from WSL, transfer of a prepared run and
hardware CI on a self-hosted runner. Then v0.1.0-rc.1 and v0.1.0, supervision of
server processes, evolution of the
profile schema and manifest; later a host controller for external equipment and Python
packaging. These are plans, not available features: [roadmap](../../TODO.md)
(Russian), [versioning rules](VERSIONING.md), [getting started](GETTING_STARTED.md).

## Check history

**ELF load section regression, 2026-09-24.** Host 53/53, including nine checks of
gaps, LMA, bounds and read errors with a refusal before the server. Stand project:
F411CE/ST-Link/OpenOCD 22/22, F103C8/J-Link 22/22; firmware left in reset/run. The
non-loaded gap case was checked with a host fixture and an offline analysis of a saved
K1921 ELF without connecting a stand. Policy — [images and CRC](IMAGES.md).

**Full image and CRC, 2026-09-25.** Host 65/65. The full 16 KiB was verified on
F411CE/ST-Link/OpenOCD and F103C8/J-Link: programming an 0xA5 tail, a repeat without
programming, the expected verify-only ERROR with an 0xFF policy, 0xFF restore, HW_BOOT
and HW_GPIO with HAL macros after a real container load. The CRC is computed on the
host over the readback. The full 22-scenario suites were not repeated at that stage.
Protocol — FULL_IMAGE_CRC.md in the stand project.

**F030R8 / Cortex-M0, 2026-09-25.** J-Link mapping `STM32F030R8`, J-Link GDB Server
8.32, on-board J-Link STLink, SWD. The stand project passed 17 scenarios, programming,
readback and reset/run; host 65. The profile schema is unchanged: HardFault and the
diagnostic registers available on M0, without CFSR/HFSR. This does not check every
Cortex-M0 or every F0 backend combination.
[Consumer protocol](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/F030_JLINK_VALIDATION.md) (Russian).
