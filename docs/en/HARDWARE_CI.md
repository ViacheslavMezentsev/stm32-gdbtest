# Prepared runs, hardware CI and 24/7 runs

[Documentation](index.md) → Hardware CI · [Русский](../ru/HARDWARE_CI.md)

Build and preparation happen where the toolchain is (a workstation, CI), and the run
happens on the stand where the debuggers are connected. One file travels between them —
a **prepared run package**. Manual transfer, hardware CI on a self-hosted GitHub runner
and repeated runs on a stand are built on it. Requirements: items 5.19, 8.21, 8.22 of the
[specification](../TECHNICAL_SPECIFICATION.md) (Russian); the method: [DDTT](DDTT.md),
sections 6.7, 6.8.

## Prepared run package

```powershell
python -B -m stm32_gdbtest pack --session <build>/hwtest/session.json --output build/packages/f411ce.zip
```

`pack` first prepares every scenario without hardware (`run --prepare-only`: ELF
snapshot, build manifest, contracts, image) and writes no package on any ERROR. The zip
then contains:

| File | Contents |
| --- | --- |
| `ddtt-package.json` | Schema 1: module version, creation time, ELF SHA-256, scenarios and their metadata, preparation results, SHA-256 of every file |
| `firmware.elf` | The ELF with debug information |
| `build-manifest.json` | The build manifest, when present |
| `profile/target.toml`, `profile/tests/…` | MCU profile, scenarios, `contracts.json`, `requirements.md` |
| `--include` files | Project helper modules imported by scenarios (paths relative to the project root) |

`--test ID` (repeatable) keeps only the selected scenarios. The package takes the
scenarios' `Tests` directory and the MCU description, even when the latter is a separate
file (`PROFILE`).

On the stand, run from the package instead of `session.json`:

```sh
python3 -B -m stm32_gdbtest run --package f411ce.zip --test HW_CI_BOOT --stand f411ce.local.toml
```

Every file's SHA-256 is checked before the run; an extra, changed or unsafe path (`..`,
absolute) is refused. The package is extracted into `--workdir` (default
`build/ddtt-packages/<hash>`), GDB comes from the stand (`--gdb` → `STM32_GDBTEST_GDB` →
`PATH` → `ARM_TOOLCHAIN_ROOT`). The report gets a `package` field with the package hash,
name and creation time. Nothing is rebuilt on the stand; preparation before the server
is repeated with the stand's GDB.

For the CI firmware `run_hw.py --package <file> ...` does the same: the `build` step checks
that the package holds the CI scenarios, the other steps run as usual.

## Hardware CI on a self-hosted runner

The **Hardware** workflow (`.github/workflows/hardware.yml`) runs only manually (Actions →
Hardware → Run workflow): choose the profiles and, if needed, the steps.

1. The `prepare` job on `ubuntu-24.04` installs the pinned toolchain
   (`tools/linux_stand.py`), builds the CI firmware, runs CTest `host` and `pack`, and
   keeps the packages as the `ddtt-packages` artifact.
2. The `hardware` job on a runner with the labels `self-hosted, linux, ARM64, stm32-stand`
   downloads the packages and runs `doctor` and `run_hw.py --package` for every profile.
   Results go to the `hardware-results` artifact.

The runner's stands live outside the repository: `$STM32_GDBTEST_STANDS_DIR/<profile>.toml`,
by default `~/.config/stm32-gdbtest/stands/f411ce.toml` and so on.

### Installing the runner on the Orange Pi

The [stand environment](LINUX_STAND.md) and USB access are required. In GitHub: Settings →
Actions → Runners → New self-hosted runner → Linux, ARM64; GitHub shows the download
commands and `config.sh` with a one-time token — do not store the token in files. Add the
label during configuration:

```sh
./config.sh --url https://github.com/<owner>/stm32-gdbtest --token <token> --labels stm32-stand
echo "STM32_GDBTEST_STANDS_DIR=$HOME/.config/stm32-gdbtest/stands" >> .env
sudo ./svc.sh install "$USER" && sudo ./svc.sh start
```

The runner service has no graphical session: set `startup_timeout_s = 30` in a J-Link
STLink stand or confirm the terms window beforehand
([HOWTO](HOWTO.md#linux-stand-and-orange-pi)).

### Security

The repository is public, and the runner has access to the stand and the network. So:

- the workflow runs only manually, never on `pull_request` or `push`;
- in Settings → Actions → General keep the approval requirement for outside contributors;
- the runner works as a separate user without sudo, with USB access only;
- runner stands and keys are not stored in the repository.

Remove the runner: `sudo ./svc.sh stop && sudo ./svc.sh uninstall`, then
`./config.sh remove --token <token>` (GitHub shows the removal token on the runner page).

## 24/7 runs

`run_hw.py --repeat N` repeats the selected steps N times, `--repeat 0` until Ctrl+C. The
`build` step runs once. Every iteration keeps `iterations/NNNNN.json`, and `soak.json`
holds counters: iterations, passed iterations, failures per step, the first failure, the
time of the last iteration and an interruption flag.

```sh
. ~/.local/stm32-gdbtest/env.sh
python3 -B tests/firmware/run_hw.py --profile f411ce --stand tests/firmware/stands/f411ce-openocd.local.toml \
  --steps boot gpio timeout after-recovery --repeat 0
```

For a run without an open terminal use `tmux`/`screen` or a systemd user service
(`systemd-run --user --unit=ddtt-soak …`). Steps that program Flash (`full-a5`, `full-ff`)
wear the memory: choose steps without programming for long runs.
