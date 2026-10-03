# Checks and CI

[Documentation](index.md) → Checks and CI · [Русский](../ru/testing.md)

## Evidence levels

The normative classification is main specification 9.3, not a CI command sequence.

| Level | Confirms | Does not confirm | Tools |
| --- | --- | --- | --- |
| L0 | Environment, dependency versions and hashes | Module logic | ci/docker/verify.py, doctor |
| L1 | Documents, links, RU/EN pairs and publication boundaries | Text semantics or code behavior | docs, docs.public |
| L2 | Host logic with substitutes | Actual GDB/backend/MCU | tests/host |
| L3 | CMake Configure/Generate and test registration | Compilation or execution | CMake host tests, consumer |
| L4 | ELF/images, sections and manifest | Firmware execution | CMSIS/HAL GCC matrix |
| L5 | Offline GDB, DWARF, contracts and preparation | MCU or peripherals | prepare, contract_preflight |
| L6 | Execution and recovery on a specific stand | All platforms or coverage | run_hw.py, run_suite.py |

Command groups below can span several levels; format is a separate style check.
QEMU/Renode are not implemented acceptance levels. L6 is part of release acceptance.
`docs.public` reads the designated .gitignore filters and rejects local-only material
and references into it, regardless of whether the developer has the file locally.


CI checks the module up to the GDB server: without a debugger, a board or MCU
access. Hardware scenarios run separately on an agreed stand
([maintenance](maintenance.md#working-with-hardware)). CI requirements are items
8.11–8.20 of the [specification](../TECHNICAL_SPECIFICATION.md) (Russian).

## Check levels

| Level | What is checked | Where |
| --- | --- | --- |
| docs | `check_spec.py --strict` for the specification, local Markdown links, RU/EN pairs | `ci/run_checks.py docs`, Docs workflow |
| format | C/C++ sources match `.clang-format` (`clang-format --dry-run --Werror`, version ≥ 16) | `ci/run_checks.py format` in the Docker image, Offline workflow |
| host | Module host tests `tests/host` | Linux in the Docker image, Windows (Python 3.11, 3.13) and Ubuntu 20.04 x86_64/aarch64 on the stand environment Python, Offline workflow |
| stand | Installing the Linux stand environment in a clean `ubuntu:20.04`, `doctor`, the `build` and `prepare` steps of `run_hw.py` for three profiles | `linux-stand` job of the Offline workflow on `ubuntu-24.04` and `ubuntu-24.04-arm` |
| firmware | Building the F030R8, F103C8, F411CE CI firmware with every GCC in the lock file; build manifest; CTest `host` (traceability, `prepare.<ID>` with offline contracts); full-image preparation; rejection of a too small image policy; 10 negative ELF contract variants; presence and 4-byte alignment of load sections, including `.data` | `ci/run_checks.py firmware` in the Docker image, Offline workflow |
| hal | HAL F030/GCC13: 24 CTest, 22 prepare JSON, positive and 5 negative contracts; no server | `ci/run_checks.py hal`, Offline workflow |

The CI firmware lives in [tests/firmware](../../tests/firmware/README.md): CMSIS without
HAL and without stm32-cmake-yml, one profile each for Cortex-M0, M3 and M4. The
scenarios check register state and are not evidence of HAL behaviour. The hardware
run of 2026-09-28 is recorded in the [status page](STATUS.md#hardware-check-of-the-ci-firmware-2026-09-28).

Results go to `build/ci/summary.json`; logs to `tests/firmware/build/<profile>-gcc<version>/ci.log`.
On GitHub they are kept as the `offline-results` artifact.

## Environment

The image `ci/docker/Dockerfile` is built from the pinned [lock file](../../ci/dependencies.lock.json):
Ubuntu 24.04 by digest, xPack GCC 13.3.1-1.1, 14.2.1-1.1, 15.2.1-1.1 (each with
`arm-none-eabi-gdb-py3`), CMake 3.28.3, Ninja 1.12.1, CMSIS from STM32CubeF0 1.11.6,
F1 1.8.7 and F4 1.28.3 (F1/F4: `Drivers/CMSIS` only; F0: also HAL) and the embedded-tech-spec skill's
`check_spec.py`. GCC and CMake versions match stm32-cmake-yml; CMake 3.19.8 is not
used because the module needs CMake ≥ 3.25. Archives are checked by SHA-256,
repositories by commit. While building, the image checks GDB-Python of every GCC.

## Running locally

Docker Desktop (Windows) or Docker Engine (Linux), from the repository root:

```powershell
docker build -f ci/docker/Dockerfile -t stm32-gdbtest-ci:local .
docker run --rm --network none --mount "type=bind,source=${PWD},target=/workspace" `
  stm32-gdbtest-ci:local python3 ci/run_checks.py
```

On Linux the line continuation is `\`; to own the files as the current user add
`--user "$(id -u):$(id -g)" -e HOME=/tmp`. Selective run:
`python3 ci/run_checks.py firmware --gcc 13.3.1-1.1 --profile f411ce`.
Without arguments all levels run. The docs level uses `CHECK_SPEC` from the image.

If Docker Hub is not reachable, pass a mirror of the same Ubuntu 24.04 image:
`--build-arg BASE_IMAGE=<mirror>/ubuntu:24.04`. The default is pinned by digest.

Without Docker: host tests — `python -B -m unittest discover -s tests/host -v`;
CI firmware — the presets in `tests/firmware` (`cmake --preset f411ce`,
`cmake --build --preset f411ce`, `ctest --preset f411ce-offline`) with
`ARM_TOOLCHAIN_ROOT` and `STM32CUBE_REPOSITORY` set.

## GitHub Actions workflows

- **Docs** — on every push to any branch: the docs level.
- **Offline** — on a push to any branch except Markdown-only, `LICENSE` and
  `.github/FUNDING.yml` changes: host tests on `windows-2022` (Python 3.11 and 3.13)
  and the format, host, firmware and hal levels in the Docker image on `ubuntu-24.04` without
  network (`--network none`); the `linux-stand` job installs the stand environment in
  an `ubuntu:20.04` container (pinned by digest) on x86_64 and aarch64 (network is needed to download
  the pinned archives).
- **Hardware** — manual only: build and `pack` on `ubuntu-24.04`, then run the packages on
  a self-hosted runner with a stand ([hardware CI](HARDWARE_CI.md)).

There is no branch-prefix filter: branches of new agents are checked without
editing the workflows. A check result belongs to a specific commit; match it to
the branch's latest commit before merging.

## Hardware check of the CI firmware (development)

Separately from CI the same firmware is checked on a local Windows or Linux stand
with `tests/firmware/run_hw.py`. It builds a profile, runs the scenarios through the
regular runner and GDB server and checks the expected outcome of every step:
programming and a repeat without programming, strict identity, a full image with an
0xA5 tail, the expected verify-only ERROR, 0xFF restore, timeout with recovery and a
PASS afterwards.

```powershell
python -B tests/firmware/run_hw.py --profile f411ce --stand tests/firmware/stands/f411ce-openocd.local.toml
```

The stand is a local copy of a template from `tests/firmware/stands/*.example.toml`
(`*.local.toml` is not committed). Toolchain and Cube — `--toolchain`, `--cube` or
`ARM_TOOLCHAIN_ROOT`, `STM32CUBE_REPOSITORY`; on Linux the stand environment's `env.sh`
sets them ([Linux stand](LINUX_STAND.md)), on Windows there are defaults in the user
profile. `summary.json` records the host OS and architecture. The result is `build/hw/<profile>-<stand>/summary.json`.
The script reprograms Flash: use only boards agreed for experiments.

## What CI does not check

- Connecting to a GDB server, debugger and MCU, Flash programming, identity, the
  Target API at run time, timeout/recovery — these are the consumer's hardware checks.
- Debugger locking between processes — only by the Windows and Linux host tests.
- The remote GDB server through real SSH: host tests check the SSH options and the
  helper script without SSH; an end-to-end run over SSH is checked manually on a stand
  ([Linux stand](LINUX_STAND.md)).
- HAL semantics and correctness of scenarios on a board: contracts check the
  presence of symbols, types and macro expansion in the ELF.

## F030 HAL in offline CI

`python -B ci/run_checks.py hal` builds tests/hal-f030 with GCC13.3.1, requires
exactly19 CTest checks (17 prepare + trace + fixture), and validates17 fresh JSON
reports with ELF hashes and no hardware access. Requested contracts must PASS;
NOT_REQUESTED for cases without contracts is not HAL validation.

A positive preflight precedes five independent errors: missing macro, wrong macro
context, HAL_ADC_Start_DMA return type, HAL_ERROR enum value and
HAL_ADC_ConvCpltCallback argument type. Each must produce ERROR in the mutated
contract. No server starts and no MCU firmware executes.

Docker installs the HAL F0 gitlink from the existing pinned CubeF0 1.11.6;
F1/F4 remain CMSIS-only. Workflow runs `format host firmware hal` and retains
tests/hal-f030/build/ci-gcc13 (logs, ELF, manifest, JSON/JUnit).
The default runner also includes hal; --gcc/--profile only restrict the CMSIS
matrix. For HAL use ARM_TOOLCHAIN_ROOT pointing to GCC13 and STM32CUBE_REPOSITORY;
otherwise the Windows/Linux GCC13 default is used. HAL GCC14/15 and hardware
regression remain separate tasks.

For rc.2 acceptance see the [matrix](RC2_READINESS.md). `tests/firmware/run_hw.py`
uses boot/GPIO to exercise the runner; the full F030 suite is run separately.
