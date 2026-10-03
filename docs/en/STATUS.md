# stm32-gdbtest status

[Documentation](index.md) → Status · [Русский](../ru/STATUS.md)

[First API package integrated](../research/api-extension/en/core-integration.md): 0.2.0.dev0, API spec 0.2.2/system 0.62; host/offline and three stands PASS. Release separate. Historical stages follow.

[F429 RTC/Sleep/deadline/recovery:20/20 HW +5 repeats, external timeout/recovery and HAL restore PASS; specification0.57.](F429_CMSIS_RTC_SLEEP.md)

[F429 ADC/DMA/units/failures:15/15 HW +3 repeats, HAL restored; specification0.56.](F429_CMSIS_ADC_DMA.md)

[F429 CMSIS baseline:7/7 HW, HAL restored; specification0.55. Fifth CI profile; ADC/RTC remain pending.](F429_CMSIS_BASELINE.md)

[F401 RTC/Sleep/deadline/recovery:20/20 HW +5 repeats, external timeout/recovery and HAL restore PASS; specification0.54.](F401_CMSIS_RTC_SLEEP.md)

[F401 ADC/DMA/units/failures:15/15 HW and three positive repeats, HAL restored; specification0.53.](F401_CMSIS_ADC_DMA.md)

[F401 CMSIS baseline: 7/7 HW through ST-Link/OpenOCD, HAL boot/blink restored. Flash256/RAM64; ADC/RTC are not migrated yet.](F401_CMSIS_BASELINE.md)

rc.2 snapshot: 5b7b466. Docs/Offline/Hardware SUCCESS; all 27 GitHub JSON reports verified.
Windows: F030 CMSIS 18/18, HAL 17/17 with repeats/recovery; F030/OpenOCD,
F103/J-Link and F411/OpenOCD lifecycles — 10/10 each. ST server completed after
USB reconnect, not an uninterrupted 10/10; the USB failure cause is unknown.
All original HAL images restored. [Evidence and remaining gates](RC2_READINESS.md).

rc.2 published at a0d6547. Post-tag F103 baseline (352417c) and ADC/DMA
(3e123ad) landed. New [RTC/Sleep](F103_CMSIS_RTC_SLEEP.md):
20/20 HW, five positive repeats, timeout/recovery and HAL restore PASS.
Initial restore ACL errors are preserved in the evidence.

## Current scope and evidence

| Area | Verified scope and limits |
| --- | --- |
| Host | 98 unittests; Windows: 8 platform skips. Linux skips Windows-only checks; exact results are logged, skips do not count as HW PASS |
| Offline CI | Docs, format, host; CMSIS F030/F103/F411 × GCC13/14/15; separate GCC13 HAL F030, 19 CTest checks and 5 negative contracts. All five Offline jobs passed at 5b7b466 |
| CMSIS F030 | 18 cases: boot/clock/GPIO/blink, TIM3, ADC/DMA/numeric vectors, Sleep, RTC and failures. HW: one complete 18/18 run at 5b7b466 locally on Windows; HAL restored. Earlier SSH/Orange Pi run at a48158c; see RC2_READINESS |
| HAL F030 | Standalone tests/hal-f030: 17/17, six post-injection repeats, expected timeout ERROR, recovery and consumer HAL restoration — Windows/ST-Link/OpenOCD |
| CMSIS F103/F411 | Post-rc.2: F103 20/20 HW clocks/GPIO/SysTick/TIM2/ADC/DMA/RTC/Sleep + 5 normal repeats, timeout/recovery; F411 has 20/20 HW baseline/ADC/DMA/RTC/Sleep +5 repeats, timeout/recovery, HAL restored. Full migration remains incomplete |
| minimal-consumer F411 | Separate CMake integration example without YAML; demonstrates module integration, not complete board peripherals |
| BlackPill consumer | fb2d186 / module 67b7431: Offline SUCCESS, five profiles/120 CTest; Windows 25/25, F411/OpenOCD 22/22 + timeout/recovery/restore. Final gitlink follows module land |

Sources: [HAL→CMSIS](F030_CMSIS_ACCEPTANCE.md), [HAL protocol](F030_HAL_VALIDATION.md),
[techniques](TESTING_TECHNIQUES.md), [CI](testing.md).
The current Nucleo stand uses native ST-Link/OpenOCD; J-Link STLink results below are historical.
F103 is WeAct BluePill-Plus/J-Link; F411 is BlackPill/ST-Link with OpenOCD and ST server.
Remote runs, packages and the Hardware workflow were repeated for rc.2;
exact SHAs and scope are in RC2_READINESS. A standalone Linux PC with USB and WSL usbipd
remain unverified configurations. Case counts are not code coverage percentages.

## Stand layouts

Local Windows and Orange Pi 5/Linux, Windows/WSL → server over SSH,
pack/run --package and the Hardware workflow are implemented and were checked
for rc.1. The historical matrix below is not final rc.2 acceptance.
rc.2 acceptance completed according to the [release matrix](RC2_READINESS.md).

## Final check of 0.1.0-rc.1, 2026-09-29

Historical rc.1 check: commit `2143665` (version `0.1.0rc1`).
These results do not automatically apply to changes made after rc.1.

| Check | Result |
| --- | --- |
| CI: Docs, Offline (format, host Windows/Linux, CI firmware on GCC 13/14/15, Linux stand environment) | green |
| `run_hw.py` on Windows: F030R8 / J-Link STLink, F103C8 / J-Link CE, F411CE / OpenOCD, F411CE / ST-LINK GDB Server | 4 × 10/10 |
| `run_hw.py` from Windows, GDB servers on Orange Pi 5 over SSH: F030R8 / J-Link, F103C8 / J-Link, F411CE / OpenOCD | 3 × 10/10 |
| Hardware workflow: packages built on GitHub, run on the Orange Pi 5 runner service | 3 × 10/10 |
| STM32G474 consumer project, runner on Windows, OpenOCD on Orange Pi 5: CTest host 5/5, scenarios on the board | 4/4 PASS |

On NUCLEO-F030R8, J-Link STLink on Windows shows a terms-of-use window; confirm it
before the run, otherwise the connection waits for the answer.

## Hardware check of the CI firmware, 2026-09-28

Commit `fbc103d`, `tests/firmware/run_hw.py`, xPack GCC 13.3.1-1.1. Every stand passed
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
sections only; before the release the hardware check was repeated on the final commit
(item 8.19 of the [specification](../TECHNICAL_SPECIFICATION.md), section above). The
stm32-hwtest-blackpill suite was not repeated on these commits.

## Implementation limits

- Hardware runs on Windows and Linux x86_64/aarch64 (glibc ≥ 2.31); on Linux they are
  checked on Orange Pi 5 (aarch64) with OpenOCD, J-Link CE and J-Link STLink; Linux x86_64 only as the
  run side in WSL2 with the server on the Orange Pi, not with a local debugger. The GDB server runs on the runner's
  computer or on a Linux stand host over SSH (`[remote]`); the remote mode is checked from
  Windows and WSL2 to Orange Pi 5; a lost link checked by pulling the Orange Pi cable: the heartbeat stopped the server after 13 s. Ninja, one firmware target and one MCU and debugger per run.
- ST-LINK GDB Server is unavailable on Linux aarch64 (ST does not release it for arm64).
- The build manifest uses Cube and CMSIS metadata; a universal build system and an
  arbitrary toolchain are not claimed.
- J-Link mapping verified for STM32F103C8T6 → STM32F103C8, STM32F030R8T6 → STM32F030R8 and
  STM32F103CBT6 → STM32F103CB (WeAct BluePill-Plus, the stm32-hwtest-bluepill demo project).
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

Prepare [rc.2](RC2_READINESS.md), then continue CMSIS migration and the
[roadmap](../../TODO.md). RISC-V, external stand control and Python packaging
remain planned work.


## Previous verification summary (before rc.2 review)

| Area | Verified scope |
| --- | --- |
| CI (GitHub Actions, Docker) | Docs, format, host on Windows and Linux; F030R8/F103C8/F411CE CI firmware with GCC 13.3.1, 14.2.1, 15.2.1 and CMake 3.28.3: build manifest, `prepare`, full image, 10 negative contracts, load section alignment, empty RAM section; the Linux stand environment in `ubuntu:20.04` on x86_64 and aarch64 ([checks and CI](testing.md)) |
| CI firmware on hardware | Final check at `2143665`: 4 stands on Windows, 3 stands from Windows to Orange Pi 5, 3 stands in the Hardware workflow — 10/10 steps each; earlier 4 stands at `fbc103d` (sections below) |
| Linux stand without hardware | Ubuntu 20.04 x86_64 (glibc 2.31, Python 3.8, git 2.25) in a container: environment installation, host tests (79 at revision 0.7), `doctor`, `build` and `prepare` of the CI firmware; the hardware path without a debugger — lock, OpenOCD start, ERROR "exited before ready", processes stopped |
| Remote GDB server on hardware | Runner and GDB on Windows 10, GDB servers on Orange Pi 5 over SSH: F411CE / OpenOCD, F103C8 / J-Link CE, F030R8 / J-Link STLink — 10/10 each (`run_hw.py`) |
| Remote GDB server without hardware | SSH loopback (OpenSSH, key, `known_hosts`) and a fake J-Link server: port forwarding, GDB connecting through the tunnel, recovery, stopping the server and returning its log, refusal on a busy stand host lock, cleanup after a broken session |
| Linux stand on hardware | Orange Pi 5, Ubuntu 20.04 aarch64, `run_hw.py`: F411CE / ST-Link V2J43M28 / xPack OpenOCD 0.12.0-7 — 10/10; F103C8 / J-Link CE V9 / J-Link GDB Server 8.32 arm64 — 10/10; F030R8 / J-Link STLink V21 / J-Link GDB Server 9.80 arm64 — 10/10 after confirming the J-Link STLink terms window in a graphical session; without it the connection waits about 10 s, the first run gave 2/10 ([Linux stand](LINUX_STAND.md)) |
| ELF/HAL preflight | Positive case and 11 negative variants on F103C8/F401CC/F411CE ELF files of the stand project |
| Stand project, F411CE / ST-Link / OpenOCD | 24/24 CTest (22 HW + 2 host) after the module split |
| Stand project, F103C8 / J-Link | 24/24 CTest (22 HW + 2 host) |
| Stand project, F030R8 / J-Link STLink | 17/17 HW |
| Stand project, F429ZI / ST-Link/V2 | 22/22 HW through OpenOCD and the ST server with module `b76d909`; occasional USB failures in long series ([protocol](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/F429_SERVER_STABILITY.md), Russian) |
| Independent F411 consumer | Build and offline, hardware scenario, verify-only, timeout/recovery and restoring the main firmware |
| Consumer project, STM32G474 / ST-Link through Orange Pi 5 | Arduino Core STM32 (HAL and CMSIS not from STM32Cube), stm32-cmake-yml with CRC in the ELF after linking, C++ with LTO, xPack GCC 14.2.1 (GDB 15.2.90, Python 3.12.8); runner on Windows, OpenOCD on the Orange Pi over SSH. Four scenarios PASS on one build without LTO: boot (DEV_ID `0x469`, IWDG frozen while halted), `setup()` completion, 15 `setup()` calls in order, power-fault injection with `force_return` — the first hardware check of `force_return`. The connection found the manifest refusal without STM32Cube packages (fixed, specification 0.16) |
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

[F411 CMSIS baseline](F411_CMSIS_BASELINE.md): HSI16, PC13, SysTick, TIM2; post-rc.2.

[F411 ADC/DMA](F411_CMSIS_ADC_DMA.md): factory calibration, numerical vectors and state faults.

[F411 RTC/Sleep](F411_CMSIS_RTC_SLEEP.md): calendar Alarm A, WFI and recovery.

[Five-profile acceptance review and remaining HAL checks](CMSIS_ACCEPTANCE.md).

[HAL F030: five GPIO/RCC techniques and source variants](F030_HAL_GPIO_RCC.md).
