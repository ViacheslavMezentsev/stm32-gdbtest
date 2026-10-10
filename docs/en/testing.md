# Checks and CI

[Documentation](index.md) → Checks and CI · [Русский](../ru/testing.md)

[Practical Docker and L6 workflow](local-ci.md): snapshot, volume, evidence and stand restoration.

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
| firmware | Building the F030R8, F103C8, F401CC, F411CE, F429ZI, AT32F403A CI firmware with every GCC in the lock file; build manifest; CTest `host` (traceability, `prepare.<ID>` with offline contracts); full-image preparation; rejection of a too small image policy; 10 negative ELF contract variants; presence and 4-byte alignment of load sections, including `.data` | `ci/run_checks.py firmware` in the Docker image, Offline workflow |
| hal | HAL F030/GCC13: 24 CTest, 22 prepare JSON, positive and 5 negative contracts; no server | `ci/run_checks.py hal`, Offline workflow |

The CI firmware lives in [tests/firmware](../../tests/firmware/README.md): CMSIS without
HAL and without stm32-cmake-yml, one profile each for Cortex-M0, M3 and M4. The
scenarios check register state and are not evidence of HAL behaviour. The hardware
run of 2026-09-28 is recorded in the [status page](STATUS_ARCHIVE.md#hardware-check-of-the-ci-firmware-2026-09-28).

Results go to `build/ci/<run>/summary.json`; logs to `tests/firmware/build/ci/<run>/<profile>-gcc<version>/ci.log`.
On GitHub they are kept as the `offline-results` artifact.

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

[Check details and commands](local-ci.md#f030-hal-in-offline-ci).
