# Checks and CI

Documentation → Checks and CI · [Русский](../ru/testing.md)

CI checks the module up to the GDB server: without a debugger, a board or MCU
access. Hardware scenarios run separately on an agreed stand
([maintenance](maintenance.md#working-with-hardware)). CI requirements are items
8.11–8.16 of the [specification](../TECHNICAL_SPECIFICATION.md) (Russian).

## Check levels

| Level | What is checked | Where |
| --- | --- | --- |
| docs | `check_spec.py --strict` for the specification, local Markdown links, RU/EN pairs | `ci/run_checks.py docs`, Docs workflow |
| host | Module host tests `Tests/host` | Linux in the Docker image and Windows (Python 3.11, 3.13), Offline workflow |
| firmware | Building the F030R8, F103C8, F411CE CI firmware with every GCC in the lock file; build manifest; CTest `host` (traceability, `prepare.<ID>` with offline contracts); full-image preparation; rejection of a too small image policy; 10 negative ELF contract variants | `ci/run_checks.py firmware` in the Docker image, Offline workflow |

The CI firmware lives in [Tests/firmware](../../Tests/firmware/README.md): CMSIS without
HAL and without stm32-cmake-yml, one profile each for Cortex-M0, M3 and M4. Its
scenarios were not run on hardware and are not evidence of HAL behaviour.

Results go to `build/ci/summary.json`; logs to `Tests/firmware/build/<profile>-gcc<version>/ci.log`.
On GitHub they are kept as the `offline-results` artifact.

## Environment

The image `ci/docker/Dockerfile` is built from the pinned [lock file](../../ci/dependencies.lock.json):
Ubuntu 24.04 by digest, xPack GCC 13.3.1-1.1, 14.2.1-1.1, 15.2.1-1.1 (each with
`arm-none-eabi-gdb-py3`), CMake 3.28.3, Ninja 1.12.1, CMSIS from STM32CubeF0 1.11.6,
F1 1.8.7 and F4 1.28.3 (`Drivers/CMSIS` only) and the embedded-tech-spec skill's
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

Without Docker: host tests — `python -B -m unittest discover -s Tests/host -v`;
CI firmware — the presets in `Tests/firmware` (`cmake --preset f411ce`,
`cmake --build --preset f411ce`, `ctest --preset f411ce-offline`) with
`ARM_TOOLCHAIN_ROOT` and `STM32CUBE_REPOSITORY` set.

## GitHub Actions workflows

- **Docs** — on every push to any branch: the docs level.
- **Offline** — on a push to any branch except Markdown-only, `LICENSE` and
  `.github/FUNDING.yml` changes: host tests on `windows-2022` (Python 3.11 and 3.13)
  and the host and firmware levels in the Docker image on `ubuntu-24.04` without
  network (`--network none`).

There is no branch-prefix filter: branches of new agents are checked without
editing the workflows. A check result belongs to a specific commit; match it to
the branch's latest commit before merging.

## What CI does not check

- Connecting to a GDB server, debugger and MCU, Flash programming, identity, the
  Target API at run time, timeout/recovery — these are the consumer's hardware checks.
- Debugger locking between processes — only by the Windows host tests.
- HAL semantics and correctness of scenarios on a board: contracts check the
  presence of symbols, types and macro expansion in the ELF.
