# stm32-gdbtest

[![Docs](https://img.shields.io/github/actions/workflow/status/ViacheslavMezentsev/stm32-gdbtest/docs.yml?branch=main&label=Docs&style=flat-square)](https://github.com/ViacheslavMezentsev/stm32-gdbtest/actions/workflows/docs.yml)
[![Offline](https://img.shields.io/github/actions/workflow/status/ViacheslavMezentsev/stm32-gdbtest/offline.yml?branch=main&label=Offline&style=flat-square)](https://github.com/ViacheslavMezentsev/stm32-gdbtest/actions/workflows/offline.yml)

[![Hardware evidence](https://img.shields.io/badge/Hardware-historical%20snapshot-blue?style=flat-square)](docs/en/HARDWARE_METRICS.md)
[![Board models tested](https://img.shields.io/badge/Boards%20tested-5-blue?style=flat-square)](docs/en/HARDWARE_METRICS.md)
[![Recorded hardware cases](https://img.shields.io/badge/HW%20cases%20%28recorded%29-98-blue?style=flat-square)](docs/en/HARDWARE_METRICS.md)
[![Latest recorded hardware verification](https://img.shields.io/badge/HW%20verified%20%28latest%29-2026--10--01-blue?style=flat-square)](docs/en/HARDWARE_METRICS.md)

[Русский](README.md)

**stm32-gdbtest implements [DDTT](docs/en/DDTT.md) for STM32: checks of running firmware
on a real board through GDB and an SWD debugger, written as scenarios in the project
repository.** A developer or an AI agent writes a scenario; it runs in GDB on the
computer, controls the firmware through a debug server and produces a JSON/JUnit
report. There is no test code in the firmware. The same scenario runs manually, from
CTest, in a CI runner or in a loop on a stand — with any connection layout: the
debugger at the workstation, on a Linux stand such as an Orange Pi, or on a remote
stand over SSH.

DDTT (debugger-driven testing on target) is a method described by its own
[specification](docs/en/DDTT.md); this repository is its reference implementation. It is
not an MCU simulator and not a unit-test framework that runs test functions inside the
firmware. It needs a
built ELF with debug information, an MCU profile and a stand.

## Why this approach

An agent can design a change and use GDB directly, but a check recorded only in a chat
is hard to reproduce. Here actions and expectations are saved in the repository
as repeatable tests: requirement → scenario in
`tests/board` → checks without hardware (ELF contracts, image) → run on a stand → a
report that both the agent and a person read. Scenarios stay test cases of the project
and run again after every change — on any of the described stands, manually or
automatically.

With STM32 it matters to check not only computations but also peripheral setup,
interrupt handling and the application's response to status codes returned by HAL
(such as `HAL_ERROR`, `HAL_BUSY` and `HAL_TIMEOUT`). Developers already
check much of this manually in a debugger; a scenario records such actions and
expectations.

The project grew out of practical GDB-Python experiments on F1/F4 boards. The
infrastructure was extracted from the [stand project](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill)
so that other applications can use it with their own profiles and tests.

Historical videos by the author, **in Russian**:

- [Early GDB-Python testing experiments](https://www.youtube.com/watch?v=idlKlSHc0wU).
- [Unit testing for small embedded systems (debugging Python tests)](https://www.youtube.com/watch?v=_BuMmQGHol4) — demonstrates the earlier Python-test workflow.

These videos explain the origins of the approach; the module documentation describes the current API and commands.

## How it works

```mermaid
flowchart LR
    I["ELF + MCU profile + Python tests"] --> H["Host runner on the PC"]
    H --> A["GDB-Python: scenario and Target API"]
    A <--> S["GDB server"]
    S <--> D["ST-Link / J-Link"]
    D <-->|SWD| M["STM32 running the application"]
    A --> R["JSON / JUnit"]
    H --> R
```

The runner checks the input artifacts, starts the server and GDB, limits the run time
and saves the results. A scenario reaches the required point of the program, reads
variables, structures and registers and compares them with expectations. If needed it
can change a value or force a function to return to test the caller's reaction. No
test logic is added to the firmware.

## Features

- Runs scenarios through OpenOCD, ST-LINK GDB Server and J-Link GDB Server; runner and
  GDB on Windows or Linux, the GDB server next to them or on the stand's Linux host over SSH.
- Image verification and programming: by loadable ELF sections, or a full image with
  fill and CRC-32 computed on the PC ([images and CRC](docs/en/IMAGES.md)); DEV_ID and
  Flash size checks in `warn` and `strict` modes ([identity](docs/en/TARGET_IDENTITY.md)).
- Target API: hardware breakpoints, `reach` with a frame check, reading values and
  structures, `set_value` and `force_return` for injections ([API](docs/en/API.md)).
- Checks without hardware: build manifest, selective ELF/HAL contracts,
  `run --prepare-only`, requirement traceability; CI is built on them
  ([checks and CI](docs/en/testing.md)).
- Timeouts with a recovery attempt, debugger locking between processes, JSON/JUnit
  reports, CMake/CTest integration.
- Prepared run packages (`pack`, `run --package`): build in one place, run on the
  stand; hardware CI on a self-hosted runner ([hardware CI](docs/en/HARDWARE_CI.md)).

## Limitations

- **Manual GDB experience is necessary.** The author needs to understand where
  to stop, which stack frame is selected, and what `step`, `finish`, reset and
  forced return do. A scenario automates those actions; the module does not
  choose suitable observation points or expectations for the developer.
- **Scenarios are Python; GDB evaluates expressions.** Reading C/C++ expressions
  through `gdb.parse_and_eval` or Target API does not allow arbitrary C code in
  a scenario. A `do { ... } while (0)` statement macro, for example, is not an
  evaluable expression. Calling a function from an expression executes code on
  the MCU and can change state or hang; MMIO reads can also have side effects.
- **Available data depends on the ELF and current context.** `-g3` preserves macro
  definitions but cannot restore variables, types or functions removed by
  optimisation. A HAL/CMSIS macro needs a source location in a compilation unit
  where it is defined; entering another function or changing the frame may make
  it unavailable. A contract checks macro presence and expansion, not the safety
  of evaluating it on hardware. See [macros](docs/en/HAL_MACRO_GUIDE.md) and
  [testing techniques](docs/en/TESTING_TECHNIQUES.md).
- **Debugging changes system behaviour.** Stops, resets and injections affect
  timing and IRQs; peripherals may keep running while the core is halted.
  Sleep/WFI checks do not measure power consumption. Hardware breakpoint counts
  are MCU-limited; optimisation and backends affect reachability and
  `finish`/`force_return` behaviour.
- **A working, agreed stand is required.** USB/SWD loss or a stuck server can
  require manual reconnection; timeout/recovery cannot guarantee physical link
  recovery. Such a case is recorded in [rc.2 acceptance](docs/en/RC2_READINESS.md).
  Support is verified for a specific MCU, build, GDB and backend combination.
- **Results apply to the scenario's conditions.** Injecting a HAL return code
  checks an application branch, not the physical cause of a peripheral failure.
  The module does not replace measuring instruments or calculate coverage
  automatically; PASS does not mean all of HAL or every device mode was tested.

## Run layouts

The scenario and the report are the same in every layout; only the local stand file
(`*.local.toml`, `remote.toml`) changes, and it stays with the user.

| Layout | Runner and GDB | GDB server and debugger | Status |
| --- | --- | --- | --- |
| Local on Windows | Windows | same computer | verified: 4 stands |
| Local on a Linux stand | Orange Pi 5, Ubuntu 20.04 aarch64 | same computer | verified: 3 stands |
| Remote server from Windows | Windows | Orange Pi 5 over SSH (`[remote]`) | verified: 3 stands and the consumer project |
| Remote server from WSL2 | WSL2, Ubuntu 20.04 x86_64 | Orange Pi 5 over SSH | verified: 3 stands |
| Prepared run package | build on Windows or in GitHub Actions | Orange Pi 5, `run --package` | verified: 3 stands |
| Hardware CI | prepare on GitHub, hardware on a self-hosted runner | Orange Pi 5 (runner service) | verified: 3 stands |
| Local on Linux x86_64 | Linux PC | same computer | implemented, not verified on hardware |
| WSL2 with the debugger via usbipd-win | WSL2 | same computer | implemented as Linux, not verified |

### Local run: Windows or Linux

Runner, GDB-Python and server share one computer. This covers Windows
and Orange Pi; local Linux x86_64 has not yet been verified on hardware.

```mermaid
flowchart LR
    subgraph PC["Computer: Windows / Linux"]
        R["Runner + GDB-Python"] <--> S["GDB server"]
        R --> O["Report"]
    end
    S <-->|USB| D["Debugger"]
    D <-->|SWD| M["STM32"]
```

### Remote server: Windows or WSL2 → Linux stand

Runner and scenario stay on the workstation. SSH starts the server on the stand
and tunnels the GDB connection. The debugger is physically attached to the stand.

```mermaid
flowchart LR
    R["Windows / WSL2: runner + GDB-Python"] <-->|SSH tunnel| S["Linux stand: GDB server"]
    R --> O["Report"]
    S <-->|USB| D["Debugger"]
    D <-->|SWD| M["STM32"]
```

### Package: build separately from execution

A package containing ELF, profile and scenarios is transferred to the stand.
`run --package` runs both GDB-Python and the server there; reports stay there too.

```mermaid
flowchart LR
    B["Windows / GitHub: build + pack"] --> P["Package"]
    P --> R["Linux stand: run --package + GDB-Python"]
    R --> O["Report"]
    R <--> S["GDB server"]
    S <-->|USB| D["Debugger"]
    D <-->|SWD| M["STM32"]
```

### Hardware CI: GitHub and a self-hosted runner

A GitHub-hosted job builds and prepares the package without a board. A self-hosted
job on Orange Pi downloads it, runs hardware checks and uploads reports.

```mermaid
flowchart LR
    G["GitHub: build + prepare + pack"] --> A["Package artifact"]
    A --> R["Orange Pi: self-hosted runner + GDB-Python"]
    R --> O["GitHub: reports"]
    R <--> S["GDB server"]
    S <-->|USB| D["Debugger"]
    D <-->|SWD| M["STM32"]
```

### WSL2 USB forwarding: not hardware-verified

All test processes run in WSL2; Windows forwards the USB device into Linux
through usbipd-win. This distinct layout has not yet been verified on boards.

```mermaid
flowchart LR
    W["WSL2: runner + GDB-Python + server"] <-->|usbipd-win| D["Debugger: USB Windows"]
    W --> O["Report"]
    D <-->|SWD| M["STM32"]
```

Remote mode uses SSH keys only; the debugger lock is held on the stand host and the
link is watched by a heartbeat. ST-LINK GDB Server is not available on Linux aarch64
(ST does not ship it for arm64), so OpenOCD and J-Link are used on Orange Pi.
Details: [Linux stand](docs/en/LINUX_STAND.md), [GDB servers](docs/en/BACKENDS.md).

**Reading the counters.** `Hardware: historical snapshot`, `Boards tested` and `HW cases (recorded)` describe recorded CMSIS hardware evidence: five board models and 98 distinct profile/fixture/scenario combinations. Repeats and builds do not increase this count; `HW verified (latest)` is the date of the newest included experiment. This is a historical snapshot across revisions, not a single run of current main or a coverage percentage. See the [metric definitions and results table](docs/en/HARDWARE_METRICS.md) for scope and evidence.

## MCU profiles

A profile is a `target.toml` file describing a specific MCU: Flash, DEV_ID, number of
hardware breakpoints, fault handlers, diagnostic registers, the OpenOCD target. The
module has no ready-made profile library "for any STM32": the consumer writes a profile
for their board, using one of the existing ones as a template. Several MCU variants of
one firmware can share scenarios, each with its own profile (`PROFILE`).

Templates in the repository: the CI firmware `tests/firmware/profiles/` (F030R8,
F103C8, F401CC, F411CE, F429ZI — Cortex-M0, M3, M4) and the example `examples/minimal-consumer/profile/` (F411CE).

| MCU | Debugger / GDB server | Verified in |
| --- | --- | --- |
| STM32F030R8 | J-Link STLink / J-Link GDB Server | CI firmware, stand project |
| STM32F103C8 | J-Link CE / J-Link GDB Server | CI firmware, stand project |
| STM32F103CB | J-Link CE / J-Link GDB Server | demo project [stm32-hwtest-bluepill](https://github.com/ViacheslavMezentsev/stm32-hwtest-bluepill) |
| STM32F401CC | ST-Link / OpenOCD | [CMSIS: 20 cases](docs/en/F401_CMSIS_RTC_SLEEP.md) |
| STM32F429ZI | ST-Link / OpenOCD | [CMSIS: 20 cases](docs/en/F429_CMSIS_RTC_SLEEP.md) |
| STM32F411CE | ST-Link / OpenOCD and ST-LINK GDB Server | CI firmware, example, stand project |
| STM32F429ZI | ST-Link / OpenOCD and ST-LINK GDB Server | stand project |
| STM32F401CC | ST-Link / ST-LINK GDB Server | stand project, earlier checks |
| STM32G474CE | ST-Link / OpenOCD on Orange Pi 5 | consumer project (Arduino Core STM32) |

OpenOCD and ST-LINK GDB Server need only the profile. J-Link GDB Server requires a
device name mapping, which currently exists for STM32F103C8T6, STM32F030R8T6 and
STM32F103CBT6. H503 is not supported. Support is defined by the specific combination
of MCU, HAL, GDB and backend, not by the family: [current status](docs/en/STATUS.md).

## Status

**0.1.0-rc.2** is published: [acceptance and limits](docs/en/RC2_READINESS.md).
Since rc.1, manifest and HAL macro contracts were fixed, CMSIS F030 was expanded,
and a standalone HAL F030 regression fixture was added. In rc.2, F103/F411 provide
basic boot/GPIO cases. Verified scope and limits: [STATUS](docs/en/STATUS.md).
The release branch uses Python version `0.1.0rc2`, `API_VERSION = 1`.
The post-rc.2 branch expands F103: clocks/GPIO/SysTick/TIM2/ADC/DMA, 15 scenarios;
[report](docs/en/F103_CMSIS_ADC_DMA.md). The published tag is unchanged.

RISC-V, full migration of other examples, external instrument control, child process
supervision and Python packaging remain in the [roadmap](TODO.md).

## Contents and dependencies

- `stm32_gdbtest/` — runner, GDB agent, Target API, backends, contracts and CMake integration.
- `tests/host`, `tests/fixtures` — infrastructure checks without a board.
- `tests/firmware`, `ci/` — F030R8/F103C8/F411CE CI firmware, Docker image, the check
  script and `run_hw.py` for hardware validation on a stand.
- `tests/hal-f030/` — standalone HAL F030 regression, CI and hardware acceptance.
- `tools/linux_stand.py` — installs the Linux stand environment without root.
- `examples/minimal-consumer/` — a standalone firmware and test example for F411.
- `docs/ru`, `docs/en` — integration, writing scenarios and mechanism descriptions;
  `docs/TECHNICAL_SPECIFICATION.md` — the specification (Russian).

You need host Python 3.11+, ARM GCC and GDB with embedded Python 3.11+, CMake 3.25+ and
Ninja, an SWD debugger and its GDB server, and the firmware libraries. HAL/CMSIS, Cube
packages and vendor tools are not part of the module. GDB-Python is a separate
interpreter, not your PC's Python environment. Linux stand: glibc ≥ 2.31 (Ubuntu 20.04
or newer), x86_64 or aarch64.

The module is integrated as a **Git submodule** (or a separate clone whose path is set
by `STM32_GDBTEST_SOURCE_DIR`). MCU settings, application tests and the local stand
stay with the consumer. Start with [integration and the example](docs/en/GETTING_STARTED.md),
then move on to [writing tests](docs/en/TEST_AUTHORING.md) — by hand or with an agent.

## Documentation and related projects

- [Documentation map](docs/en/index.md), [specification](docs/TECHNICAL_SPECIFICATION.md) (Russian).
- [API and CMake/CLI](docs/en/API.md), [ELF/HAL contracts](docs/en/CONTRACTS.md), [HAL macros](docs/en/HAL_MACRO_GUIDE.md).
- [GDB servers](docs/en/BACKENDS.md), [identity and Flash](docs/en/TARGET_IDENTITY.md), [debugger ownership](docs/en/DEBUGGER_OWNERSHIP.md), [manifest](docs/en/MANIFESTS.md), [ELF/BIN images and CRC](docs/en/IMAGES.md).
- [Status](docs/en/STATUS.md), [checks and CI](docs/en/testing.md), [versions](docs/en/VERSIONING.md), [plans](TODO.md), [changes](CHANGELOG.en.md).
- [stm32-hwtest-blackpill](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill) — firmware, hardware checks, overall architecture and practice.
- [stm32-cmake-yml](https://github.com/ViacheslavMezentsev/stm32-cmake-yml) — a related STM32 build project; not required by the module.

License — [MIT](LICENSE). [Origin](SOURCE.md), [rules for developers and agents](AGENTS.md), [maintenance](docs/en/maintenance.md).
