# Local CI: execution and evidence

[Documentation](index.md) · [Testing and CI](testing.md) · [Русский](../ru/local-ci.md)

Practical workflow for Windows/PowerShell and Docker Desktop (Linux amd64).
Normative requirements: [specification, sections 9.3–9.5](../TECHNICAL_SPECIFICATION.md).
Docker checks stop before the GDB server. L6 runs separately on an agreed Windows/Linux
stand; Linux containers do not replace native Windows regression.

## Read this first

This is the single local module-check procedure, incorporating the former local-docker-testing guide.
On Windows follow steps 1–3: **snapshot → fresh Docker volume → checks → archive**.
Both sources and builds belong in the volume. Use a bind mount only to transfer the archive;
do not run host/firmware/hal from an NTFS checkout or `/mnt/c`.
Do not start by rebuilding the image, running the entire matrix or increasing timeouts.

1. Select checks for the change: `docs` for documents, `docs host` for Python logic,
   `format` and affected matrix entries for C/C++; all groups for full acceptance.
2. Choose exactly one snapshot: a clean commit or the current working tree.
3. Reuse a verified image when its inputs are unchanged; record its ID and run L0.
4. Run the selected checks without network and without modifying the snapshot.
5. Export evidence even on failure; inspect the summary and process exit code before
   removing the created container/volume. Final-SHA GitHub CI remains mandatory.

## Selecting a run

| Task | Command inside the image | Boundary |
| --- | --- | --- |
| L0 environment | `python3 /opt/stm32-gdbtest-ci/verify.py` | Tools and pinned sources, not module behavior |
| L1 documentation | `python3 ci/run_checks.py docs` | Includes strict specs and publication filters |
| L2/L3 host | `python3 ci/run_checks.py host` | Mocks and CMake, no MCU |
| Complete offline acceptance | `python3 ci/run_checks.py` | docs/format/host, all GCC × CMSIS profiles, HAL; L1–L5 |
| L6 hardware acceptance | run_hw.py and run_suite.py on the stand | Selected MCU/backend/firmware only |

On Windows use a volume even for a small selected check set.
Run the host suite in a volume too: on 2026-10-10 the Windows working-directory bind
mount reached 600 seconds, while a separate clean snapshot in a volume passed in 26 seconds.
The difference has not been isolated to a single factor; do not raise the timeout instead of moving files. For a full Windows
matrix, place **both source and build trees in a Docker volume**. Keeping sources on
Windows can retain the I/O bottleneck. This approach comes from
[stm32-cmake-yml practice](https://github.com/ViacheslavMezentsev/stm32-cmake-yml/blob/main/docs/en/local-docker-testing.md).
Its measured speedups are not stm32-gdbtest measurements. Investigate storage before
changing scenario timeouts to compensate for slow I/O.

## 1. Image and L0

Image construction requires network; offline checks do not. Pins are in the
[lock file](../../ci/dependencies.lock.json); installation is in ci/docker/install.py.
Archive SHA-256 is checked at installation. verify.py checks versions, GDB-Python,
source commits and required files; it does not rehash original archives.
Ubuntu packages can change; installed versions are in /opt/stm32-gdbtest-ci/packages.txt.
Run from the repository root:

```powershell
$runId = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$runRoot = Join-Path $PWD.Path "build/local-checks-$runId"
$volume = "gdbtest-checks-$runId"
$exportContainer = "gdbtest-export-$runId"
New-Item -ItemType Directory -Force $runRoot | Out-Null
$image = 'stm32-gdbtest-ci:local'
# Run only if the image is absent or its build inputs changed.
# docker build --platform linux/amd64 -f ci/docker/Dockerfile -t $image .
# if ($LASTEXITCODE -ne 0) { throw 'Image build failed' }
$imageId = docker image inspect --format '{{.Id}}' $image
if ($LASTEXITCODE -ne 0) { throw 'Image inspection failed' }
docker image inspect $imageId > "$runRoot/image-inspect.json"
docker run --rm --network none $imageId 2>&1 | Tee-Object "$runRoot/L0.log"
if ($LASTEXITCODE -ne 0) { throw 'L0 failed' }
```

Reuse an existing image only when Dockerfile, lock file, install.py, entrypoint.sh and
verify.py inputs are unchanged. A tag alone is insufficient: retain image ID and build
provenance and rerun L0 even on a cache hit. Execute using the captured image ID.

## 2. Source snapshot

### Option A: clean signed commit

Acceptance uses a signed commit with a clean public tree. Ignored research and local
stands are excluded. Git archive does not copy .git and also supports linked worktrees.
It does not include submodule contents; this repository obtains SDKs from the image.
If gitlinks are introduced, use a separate snapshot recipe.

```powershell
$state = git status --porcelain
if ($LASTEXITCODE -ne 0) { throw 'Git status failed' }
if ($state) { throw 'Commit reviewed changes before acceptance snapshot' }
$sha = git rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve HEAD' }
$sha | Set-Content "$runRoot/commit.txt"
git archive --format=tar --output="$runRoot/source.tar" $sha
if ($LASTEXITCODE -ne 0) { throw 'Snapshot failed' }
Get-FileHash "$runRoot/source.tar" -Algorithm SHA256 | Format-List | Out-File "$runRoot/source-sha256.txt"
```

Do not claim git archive HEAD checks uncommitted edits. Development experiments require
a separate current-file snapshot with file inventory, SHA-256, dirty status and no edits
during packaging; that evidence is not HEAD acceptance. A fresh volume excludes stale
CMake caches and reports. Do not carry Windows builds into Linux.

### Option B: working changes

Save this fragment as `build/make-local-snapshot.py` for pre-commit checks. It includes modified
and new non-ignored files, preserves deletions, hashes the actual archived bytes and records
dirty status. Do not edit the tree while packaging. No `.git` is copied: `docs.public` handles
Git-free snapshots, so `git init/add` is unnecessary. This checks the working tree, not the
commit named by the head field.

```python
from pathlib import Path
import hashlib
import io
import json
import subprocess
import sys
import tarfile

root = Path.cwd()
out = Path(sys.argv[1]).resolve()
if not out.is_relative_to(root / "build"):
    raise SystemExit("Output must be in this checkout's ignored build directory")
out.mkdir(parents=True, exist_ok=True)
entries = subprocess.check_output(["git", "ls-files", "--stage", "-z"]).split(b"\0")
if any(entry.startswith(b"160000 ") for entry in entries):
    raise SystemExit("Gitlinks need an explicit submodule snapshot recipe")
names = subprocess.check_output([
    "git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"
]).decode("utf-8").split("\0")
manifest = {
    "kind": "working-tree",
    "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "status": subprocess.check_output(["git", "status", "--porcelain"], text=True),
    "files": {}
}
with tarfile.open(out / "source.tar", "w") as archive:
    for name in sorted(set(filter(None, names))):
        path = root / name
        if path.is_symlink():
            raise SystemExit("Symlinks need an explicit snapshot recipe: " + name)
        if not path.is_file():
            continue  # Preserve working-tree deletions.
        if path.resolve().is_relative_to(out):
            raise SystemExit("Snapshot output must be ignored by Git")
        data = path.read_bytes()
        manifest["files"][name] = hashlib.sha256(data).hexdigest()
        info = archive.gettarinfo(str(path), arcname=name)
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
manifest["archive_sha256"] = hashlib.sha256((out / "source.tar").read_bytes()).hexdigest()
(out / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
```

```powershell
python build/make-local-snapshot.py "$runRoot"
if ($LASTEXITCODE -ne 0) { throw 'Working-tree snapshot failed' }
```

### Shared step: load either snapshot

```powershell
docker volume create $volume
if ($LASTEXITCODE -ne 0) { throw 'Volume creation failed' }
docker run --rm --network none --mount "type=volume,source=$volume,target=/work" --mount "type=bind,source=$runRoot/source.tar,target=/snapshot.tar,readonly" $imageId sh -c 'mkdir -p /work/source && tar -xf /snapshot.tar -C /work/source'
if ($LASTEXITCODE -ne 0) { throw 'Snapshot extraction failed' }
```

## 3. Checks and export on failure

```powershell
# Choose one set: @('docs'), @('docs', 'host'), or @() for all groups.
$checkArgs = @('docs', 'host')
docker run --rm --network none --mount "type=volume,source=$volume,target=/work" -w /work/source $imageId python3 ci/run_checks.py @checkArgs 2>&1 | Tee-Object "$runRoot/checks.log"
$checksExit = $LASTEXITCODE
$checksExit | Set-Content "$runRoot/checks-exit.txt"
# Export even after a failed check. Include sources and all partial build evidence.
docker run --name $exportContainer --network none --mount "type=volume,source=$volume,target=/work,readonly" $imageId tar -czf /tmp/results.tar.gz -C /work source
if ($LASTEXITCODE -ne 0) { throw 'Archive failed; retain volume and container' }
docker cp "${exportContainer}:/tmp/results.tar.gz" "$runRoot/results.tar.gz"
if ($LASTEXITCODE -ne 0) { throw 'Export failed; retain volume and container' }
Get-FileHash "$runRoot/results.tar.gz" -Algorithm SHA256 | Format-List | Out-File "$runRoot/results-sha256.txt"
if ($checksExit -ne 0) { throw "Checks failed: $checksExit; evidence retained" }
```

Full matrix: `$checkArgs = @()`; docs: `@('docs')`; one profile:
`@('firmware', '--gcc', '13.3.1-1.1', '--profile', 'f411ce')`.
Inspect source/build/ci/<run>/summary.json in the archive: exit code zero, every expected
entry, no FAIL or missing combination. Without --gcc/--profile the runner uses the full
lock-file matrix; HAL is a separate GCC13 check. A subset is not full acceptance.
Independent checks continue after failure and produce a failing overall exit code;
missing evidence never means success.

Each runner invocation creates build/ci/<run> and separate tests/<fixture>/build/ci/<run> builds.
Use separate volumes for independent source snapshots. Wait for all processes before export.
After verifying the archive, remove only the created container and volume with
`docker rm $exportContainer` and `docker volume rm $volume`; no global prune is needed.
Run native Windows host separately: `python -B -m unittest discover -s tests/host -v`.
Retain Python/CMake versions and PASS/SKIP/ERROR counts; Linux does not check Windows paths/processes.

## Timing, stalls and concurrency

File placement provides the main benefit, not additional containers. During 0.4.1 preparation,
host took about 39 s for 451 tests (4 expected skips) on this machine. An earlier snapshot took
26 s; a bind-mounted run reached 600 s. These are separate observations, not a controlled
benchmark or a guaranteed deadline.

- Start sequentially. Each `ci/run_checks.py` call creates unique output directories;
  independent snapshots need separate volumes. Never extract a new snapshot over an old one:
  deleted files could remain in the container.
- `host.log` is written after the child command finishes; quiet stdout alone is not a hang.
  Inspect `docker ps`, `docker stats --no-stream`, and for the relevant container
  `docker exec <container> ps -eo pid,etime,pcpu,stat,wchan:24,args`.
  `p9_client_rpc` can indicate Windows filesystem access; inspect mounts first.
- Account separately for image build/download, archive transfer, checks and export.
  An outer process deadline, a runner subprocess timeout and an expected HW timeout differ.
- On cancellation, stop your running container with `docker stop <container>` first.
  Keep partial logs and the volume; incomplete execution is not PASS. Do not use global prune.
- Moving only build outputs leaves NTFS source reads. Do not reduce coverage or relax
  timeouts to conceal slow filesystem access.

## Linux and native checks

A bind mount is suitable on Linux when the checkout is on a native Linux filesystem.
WSL `/mnt/c` or `/mnt/d` remains Windows storage: use the volume recipe instead.
Bash alternative after image preparation, from the repository root:

```sh
set -o pipefail
mkdir -p build
run_id="$(date -u +%Y%m%dT%H%M%S)-$$"
docker run --rm --network none --user "$(id -u):$(id -g)" -e HOME=/tmp \
  --mount "type=bind,source=$PWD,target=/workspace" \
  stm32-gdbtest-ci:local python3 ci/run_checks.py docs host 2>&1 | tee "build/local-$run_id.log"
check_exit=${PIPESTATUS[0]}
exit "$check_exit"
```

Without Docker: `python -B -m unittest discover -s tests/host -v`; for firmware,
`cmake --preset f411ce`, `cmake --build --preset f411ce`, `ctest --preset f411ce-offline`
from `tests/firmware` with `ARM_TOOLCHAIN_ROOT` and `STM32CUBE_REPOSITORY` configured.
Native checks do not replace the pinned Docker matrix. Linux containers do not verify
Windows mutexes, encodings, paths or process lifecycle. The lock file defines the complete
matrix: currently 3 GCC × 6 profiles, plus HAL GCC13. `--gcc/--profile` do not limit HAL;
`stand` is a separate GitHub Offline job, not a run_checks.py argument. QEMU/Renode are not
acceptance levels for this module.

## 4. L6 before connection

1. Record MCU, board, backend, probe, connection mode, power and agreed restoration
   firmware. Keep serials and personal paths in local TOML. Match the actual board
   to its profile and exclude competing GDB servers.
2. Retain source SHA, ELF and build-manifest hashes, toolchain/GDB/embedded Python and
   server versions. Retain package hash for packaged runs. Follow doctor in the
   [stand guide](LINUX_STAND.md); doctor PASS does not establish MCU availability.
3. Prepare both test and restoration sessions offline. An unrequested contract is
   not a passed contract. Linux absolute-path manifests are not Windows builds;
   use the standard pack mechanism for transfer.
4. Specify expected outcomes and time limits before execution. One probe belongs to
   one run. Mass erase, option bytes, shared mode and probe updates are outside this procedure.

## 5. L6 execution, recovery and restoration

Full existing session suite with restoration; replace paths with actual ones:

```powershell
$session = 'tests/firmware/build/f411ce/hwtest/session.json'
$restore = $session
$stand = 'tests/firmware/stands/f411ce-openocd.local.toml'
python -B tests/firmware/run_suite.py --session $session --restore-session $restore --stand $stand
if ($LASTEXITCODE -ne 0) { throw 'Offline preparation failed' }
# Only on the agreed stand; writes firmware. Restore may be a different approved session.
python -B tests/firmware/run_suite.py --session $session --restore-session $restore --stand $stand --execute --timeout-recovery
if ($LASTEXITCODE -ne 0) { throw 'Hardware suite failed; inspect reports and restoration' }
```

--execute enables hardware. Without it summary PASS with hardware=false is not L6.
run_suite.py verifies manifest/MCU, prepares both sessions and, after starting hardware,
attempts restoration in finally with BOOT/GPIO (or BOOT/BLINK) checks. Power loss or
forced termination may interrupt finally; board state remains unknown until separately
verified restoration.

Test the runner lifecycle separately using [run_hw.py](../../tests/firmware/run_hw.py):
program/repeat, strict identity, full-image A5/FF, negative verify-only, timeout/recovery.
It neither replaces the full scenario suite nor guarantees return to the user's firmware:
arrange a separate restore in the outer run's finally and verify its reports.

Separate lifecycle command (writes firmware; arrange restoration separately):

```powershell
python -B tests/firmware/run_hw.py --profile f411ce --stand tests/firmware/stands/f411ce-openocd.local.toml
if ($LASTEXITCODE -ne 0) { throw 'Lifecycle check failed; retain reports and restore' }
```

Set toolchain/Cube with `--toolchain`, `--cube` or `ARM_TOOLCHAIN_ROOT`, `STM32CUBE_REPOSITORY`;
on Linux the stand env.sh also provides them. Result: `build/hw/<profile>-<stand>/<run>/summary.json`.

The short GDB startup timeout in run_hw.py is a separate infrastructure check; it does
not establish scenario entry, unlike the run_suite.py timeout.

Accept expected ERROR only when its cause and execution phase match, not merely exit
code 2. An in-scenario timeout must occur after entering the scenario, show host recovery and be
followed by positive GPIO. A connection failure instead is a failed check. Preserve the
original ERROR; retries do not erase it. Timeout reset_run and restoring the agreed ELF
are separate operations.

## 6. Evidence and limits

A run passport links SHA/dirty, image ID or stand versions, ELF/manifest/package hashes,
expected scenarios and actual reports, outcomes, timings, SKIP, recovery and restoration.
Overall PASS requires the complete selected set and confirmed restoration. Missing
reports, wrong MCU, cancellation or unknown board state cannot produce HW PASS.
Retain JSON/JUnit, GDB/server/host logs and the original failure before another run.

Raw logs and personal configuration stay in ignored build/local storage. Publish sanitized
accepted results without links to unavailable local files. A completed campaign is in
[rc.1 acceptance](RC020_READINESS.md); the volume recipe adds no hardware coverage.
This documentation change checks docs and the Docker recipe smoke only; it claims no new hardware runs.

## Environment

The image `ci/docker/Dockerfile` is built from the pinned [lock file](../../ci/dependencies.lock.json):
Ubuntu 24.04 by digest, xPack GCC 13.3.1-1.1, 14.2.1-1.1, 15.2.1-1.1 (each with
`arm-none-eabi-gdb-py3`), CMake 3.28.3, Ninja 1.12.1, CMSIS from STM32CubeF0 1.11.6,
F1 1.8.7 and F4 1.28.3 (F1/F4: `Drivers/CMSIS` only; F0: also HAL) and the embedded-tech-spec skill's
`check_spec.py`. GCC and CMake versions match stm32-cmake-yml; CMake 3.19.8 is not
used because the module needs CMake ≥ 3.25. Archives are checked by SHA-256,
repositories by commit. While building, the image checks GDB-Python of every GCC.


If Docker Hub is unavailable, use `--build-arg BASE_IMAGE=<mirror>/ubuntu:24.04`;
record the replacement digest and origin. Do not change other dependencies to bypass network failures.

## F030 HAL in offline CI

`python -B ci/run_checks.py hal` builds tests/hal-f030 with GCC13.3.1, requires
exactly19 CTest checks (22 prepare + trace + fixture), and validates17 fresh JSON
reports with ELF hashes and no hardware access. Requested contracts must PASS;
NOT_REQUESTED for cases without contracts is not HAL validation.

A positive preflight precedes five independent errors: missing macro, wrong macro
context, HAL_ADC_Start_DMA return type, HAL_ERROR enum value and
HAL_ADC_ConvCpltCallback argument type. Each must produce ERROR in the mutated
contract. No server starts and no MCU firmware executes.

Docker installs the HAL F0 gitlink from the existing pinned CubeF0 1.11.6;
F1/F4 remain CMSIS-only. Workflow runs `format host firmware hal` and retains
`tests/hal-f030/build/ci/<run>/` (logs, ELF, manifest, JSON/JUnit).
Each CI attempt uses a new directory on either OS.
The default runner also includes hal; --gcc/--profile only restrict the CMSIS
matrix. For HAL use ARM_TOOLCHAIN_ROOT pointing to GCC13 and STM32CUBE_REPOSITORY;
otherwise the Windows/Linux GCC13 default is used. HAL GCC14/15 and hardware
regression remain separate tasks.

For rc.2 acceptance see the [matrix](RC2_READINESS.md). `tests/firmware/run_hw.py`
uses boot/GPIO to exercise the runner; the full F030 suite is run separately.

## Docker and CI

| Problem | Solution |
| --- | --- |
| Docker Hub is unreachable while building the image | `docker build --build-arg BASE_IMAGE=<mirror>/ubuntu:24.04 …` ([local CI](local-ci.md)) |
| Files in `build/` are owned by root after a container run on Linux | Run with `--user "$(id -u):$(id -g)" -e HOME=/tmp`; preserve evidence first, then repair ownership of only your build directory |
| CI is red but everything passes locally | Match the checked commit with the branch's latest commit; open the `offline-results` or `linux-stand-*` artifact |
| Image build: `PermissionError: … 'ninja'` in `verify.py` | A file from a ZIP archive was extracted without the executable bit (Python `zipfile` does not restore Unix permissions). `install.py` restores them from the archive; after changing extraction check `ninja --version` in the built image |
| `windows-host` red, Linux green: a test compares paths | On Windows tool paths come back with `\`. Compare paths in one form in tests (`.replace("\\", "/")` or `Path`), not raw strings |
| `format`: clang-format found differences | Format the changed C/H files with `clang-format -i <files>` (the CI image version; locally easiest in the container) and rerun `python3 ci/run_checks.py format` |
| A new profile broke a host test with reference data | The test iterated every `profiles/` directory; the reference pins its profile list, and a new profile is added to the reference separately |
| The vendor SDK (Artery) is needed outside CI | `python tools/vendor_sdk.py` installs the pinned archive where CMake looks for it ([compatible MCUs](COMPATIBLE_MCU.md)) |
| The AT32 SDK is installed but `run_hw.py` says `AT32 SDK not found` | An old `AT32_SDK_ROOT` may remain in `tests/firmware/build/hw-<profile>-<stand>/CMakeCache.txt`. Check that the selected directory contains `libraries/cmsis/cm4/device_support/at32f403a_407.h`, then run `cmake -S tests/firmware -B <build-dir> -DAT32_SDK_ROOT=<sdk-dir>` and repeat the entire `run_hw.py`. Do not count results after a failed build: a stale `session.json` may point at an old ELF. Preserve the original FAIL. |
