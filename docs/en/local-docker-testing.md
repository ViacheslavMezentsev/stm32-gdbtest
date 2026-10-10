# Local checks: Docker and hardware stands

[Documentation](index.md) · [Testing and CI](testing.md) · [Русский](../ru/local-docker-testing.md)

Practical workflow for Windows/PowerShell and Docker Desktop (Linux amd64).
Normative requirements: [specification, sections 9.3–9.5](../TECHNICAL_SPECIFICATION.md).
Docker checks stop before the GDB server. L6 runs separately on an agreed Windows/Linux
stand; Linux containers do not replace native Windows regression.

## Selecting a run

| Task | Command inside the image | Boundary |
| --- | --- | --- |
| L0 environment | `python3 /opt/stm32-gdbtest-ci/verify.py` | Tools and pinned sources, not module behavior |
| L1 documentation | `python3 ci/run_checks.py docs` | Includes strict specs and publication filters |
| L2/L3 host | `python3 ci/run_checks.py host` | Mocks and CMake, no MCU |
| Complete offline acceptance | `python3 ci/run_checks.py` | docs/format/host, all GCC × CMSIS profiles, HAL; L1–L5 |
| L6 hardware acceptance | run_hw.py and run_suite.py on the stand | Selected MCU/backend/firmware only |

Bind mounts from [testing](testing.md) are suitable for short checks.
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
$runId = Get-Date -Format 'yyyyMMdd-HHmmss'
$runRoot = Join-Path $PWD.Path "build/local-checks-$runId"
$volume = "gdbtest-checks-$runId"
$exportContainer = "gdbtest-export-$runId"
New-Item -ItemType Directory -Force $runRoot | Out-Null
$image = 'stm32-gdbtest-ci:local'
# Build when image inputs changed or the image is absent.
docker build -f ci/docker/Dockerfile -t $image .
if ($LASTEXITCODE -ne 0) { throw 'Image build failed' }
$imageId = docker image inspect --format '{{.Id}}' $image
if ($LASTEXITCODE -ne 0) { throw 'Image inspection failed' }
docker image inspect $imageId > "$runRoot/image-inspect.json"
docker run --rm --network none $imageId 2>&1 | Tee-Object "$runRoot/L0.log"
if ($LASTEXITCODE -ne 0) { throw 'L0 failed' }
```

Reuse an existing image only when Dockerfile, lock file, install.py, entrypoint.sh and
verify.py inputs are unchanged. A tag alone is insufficient: retain image ID and build
provenance and rerun L0 even on a cache hit. Execute using the captured image ID.

## 2. Clean snapshot

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
docker volume create $volume
if ($LASTEXITCODE -ne 0) { throw 'Volume creation failed' }
docker run --rm --network none --mount "type=volume,source=$volume,target=/work" --mount "type=bind,source=$runRoot/source.tar,target=/snapshot.tar,readonly" $imageId sh -c 'mkdir -p /work/source && tar -xf /snapshot.tar -C /work/source'
if ($LASTEXITCODE -ne 0) { throw 'Snapshot extraction failed' }
```

Do not claim git archive HEAD checks uncommitted edits. Development experiments require
a separate current-file snapshot with file inventory, SHA-256, dirty status and no edits
during packaging; that evidence is not HEAD acceptance. A fresh volume excludes stale
CMake caches and reports. Do not carry Windows builds into Linux.

## 3. Checks and export on failure

```powershell
docker run --rm --network none --mount "type=volume,source=$volume,target=/work" -w /work/source $imageId python3 ci/run_checks.py 2>&1 | Tee-Object "$runRoot/checks.log"
$checksExit = $LASTEXITCODE
# Export even after a failed check. Include sources and all partial build evidence.
docker run --name $exportContainer --network none --mount "type=volume,source=$volume,target=/work,readonly" $imageId tar -czf /tmp/results.tar.gz -C /work source
if ($LASTEXITCODE -ne 0) { throw 'Archive failed; retain volume and container' }
docker cp "${exportContainer}:/tmp/results.tar.gz" "$runRoot/results.tar.gz"
if ($LASTEXITCODE -ne 0) { throw 'Export failed; retain volume and container' }
Get-FileHash "$runRoot/results.tar.gz" -Algorithm SHA256 | Format-List | Out-File "$runRoot/results-sha256.txt"
if ($checksExit -ne 0) { throw "Checks failed: $checksExit; evidence retained" }
```

For docs-only, replace the command with `python3 ci/run_checks.py docs`; keep the rest.
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
