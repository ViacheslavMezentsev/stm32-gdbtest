# Current stm32-gdbtest status

[Documentation](index.md) → Current status · [Русский](../ru/STATUS.md)

**As of 2026-10-10.** **v0.4.0** is published; its tag points to `9c3ff2d`.
Branch `codex/docs-041` prepares **0.4.1**: documentation and skills, with no API behaviour change.
0.4.1 is not published yet; CI of the final SHA and owner actions remain required.

| Versioned item | In preparation for 0.4.1 |
| --- | --- |
| `stm32-gdbtest` package | 0.4.1 |
| Scenario API compatibility | `API_VERSION=2` (unchanged) |
| target.toml schema | 2 (unchanged) |
| General / API specification | 0.95 / 0.3.16 |

These are not Python interpreter versions. See [version policy](VERSIONING.md),
[0.4.1 scope](../releases/v0.4.1.md), [migration from 0.3.0](API.md).

## Capabilities

Local and SSH runs, CMake/CTest, packages, Hardware CI and finite autonomous loops;
OpenOCD, ST-LINK GDB Server, st-util and J-Link. The API provides navigation, data observation,
injection, check tables and matchers, `profile`, arbitrary `record`/`records`, and `skip(reason)`.
Configuration enables capture to disk; export, integrity checking and HTML run separately.
PASS/FAIL/ERROR/SKIP are distinct outcomes.

[API reference](api/index.md) · [results](RESULTS.md) · [autonomous stand](STAND_LOOP.md) ·
[agent skills](../../skills/README.en.md).

## Recorded verification

| Snapshot | Evidence and scope |
| --- | --- |
| 0.4.1 preparation, 2026-10-10 | Docker docs + host: 6/6 groups; 451 host tests (4 expected skips); README example style PASS. No new hardware run; final-SHA GitHub CI is still pending |
| Full matrix `b1264c1` | Docker 26/26; six Windows OpenOCD/J-Link stands, 280 scenarios / 608 steps; minimal-consumer offline 3/3 and F411 GPIO PASS |
| Remote lifecycle `4cb5e0a`, scenarios through `a6b6dbd` | Windows → OrangePi/st-util 1.9.0; five STM32 boards, 233 combinations, 516 steps; 268 HW PASS and 5 expected timeout ERROR; OpenOCD BOOT/GPIO recovery 10/10 |
| Selected 0.4.0 scenarios | Six models on Windows and Linux/GitHub: separate runs totalling 24 PASS + 6 expected SKIP per layout; Windows/WSL → SSH: five boards, 20 PASS + 5 SKIP each |
| v0.4.0 CI | Docs, Offline and Hardware #14 successful at `ba10b12`; later documentation changes are not new hardware runs |
| DDTT skill, 2026-10-10 | Local consumer branches: F103CB — 12 scenarios with a passing rerun of a corrected injection; F411/F401 — 22/22 each; baseline FAIL, fixes and recovery verified. This is not CI of published consumer branches |

Do not add snapshots together. Linux-local and Hardware CI share evidence.
Scenario counts are not coverage percentages. Versions, SHAs and original failures:
[acceptance](API_ACCEPTANCE.md), [0.4.0 scenarios](API040_SCENARIOS.md), [metrics](HARDWARE_METRICS.md).
Process placement: [run layouts](RUN_LAYOUTS.md); MCU/backend: [profiles](MCU_PROFILES.md).

## Known limits and debt

- Long F411/F030 runs with ST-LINK GDB Server remain unaccepted due to repeated USB ERROR.
  The owner accepted v0.4.0 with this limit; passing OpenOCD/st-util does not resolve it.
- st-util 1.6.0 and 1.9.0 have different verified limits; see [st-util backend](backends/st-util.md).
- Linux x86_64 with local USB and WSL2/usbipd are not hardware-accepted. Each new board needs
  verification of the actual MCU, GDB, build and backend combination. H503 is not accepted.
- Binary USB serial diagnostics, the former F429 SP/SRAM anomaly and forced cleanup boundaries
  remain open. One consumer DDTT Windows prepare with `-j 2` rejected its output directory;
  sequential repetition passed, but the cause has not been isolated.
- Halt affects timing and IRQs; injection does not reproduce the physical failure cause. Recovery
  cannot guarantee reconnection. External instruments and power control remain separate tools.

[Earlier verification history](STATUS_ARCHIVE.md) is retained separately.
Further work and branch preparation: [TODO](../../TODO.md).
