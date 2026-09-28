# Linux stand

[Documentation](index.md) → Linux stand · [Русский](../ru/LINUX_STAND.md)

Hardware runs work on Linux x86_64 and aarch64 with glibc ≥ 2.31, which includes
Ubuntu 20.04. The target validation stand is an Orange Pi 5 with Ubuntu 20.04
(aarch64). The runner, the GDB server and the debugger are on one computer; a remote
server over SSH is not supported yet (question 11.2.18 of the
[specification](../TECHNICAL_SPECIFICATION.md), Russian). Requirements: items
5.4.8–5.4.11, 5.17 and 6.10 of the specification.

## Environment without root

The Ubuntu 20.04 system packages do not fit: Python 3.8 (the module needs 3.11),
CMake 3.16 (3.25 needed), OpenOCD 0.10 without `interface/stlink.cfg`. The script
`tools/linux_stand.py` installs pinned versions into a user directory (default
`~/.local/stm32-gdbtest`) and does not change the system:

| Component | Version | Source |
| --- | --- | --- |
| Python | 3.11.16 | python-build-standalone (the builds uv uses) |
| CMake / Ninja | 3.28.3 / 1.12.1 | Kitware, ninja-build |
| GNU Arm GCC with GDB-Python | xPack 13.3.1-1.1 (GDB 14.2.90, Python 3.11.4) | xPack |
| OpenOCD | xPack 0.12.0-7 | xPack |
| CMSIS | STM32CubeF0 1.11.6, F1 1.8.7, F4 1.28.3 (`Drivers/CMSIS`) | GitHub STMicroelectronics |

Archives for x86_64 and aarch64 are pinned by SHA-256 in
[tools/linux-stand.lock.json](../../tools/linux-stand.lock.json); the versions match
[CI](testing.md). The script itself runs on the system Python ≥ 3.8. It needs `curl`,
`tar` and `git`; downloads stay in `<prefix>/downloads`, and a repeated run skips
installed components.

```sh
sudo apt install -y ca-certificates curl git python3   # if something is missing
git clone https://github.com/ViacheslavMezentsev/stm32-gdbtest.git
cd stm32-gdbtest
python3 tools/linux_stand.py install
. ~/.local/stm32-gdbtest/env.sh
python3 -B -m stm32_gdbtest doctor
```

`env.sh` puts the tools first on the `PATH` of the current shell (after it `python3` is
the environment's Python 3.11) and sets `ARM_TOOLCHAIN_ROOT`, `STM32CUBE_REPOSITORY`,
`STM32_GDBTEST_GDB`. Another directory: `--prefix` or `STM32_GDBTEST_PREFIX`; some
components only: `--only python cmake …`; checking without installing:
`python3 tools/linux_stand.py verify`.

## USB access and J-Link (stand owner)

These steps need root and are done manually once:

```sh
# ST-Link: udev rules from xPack OpenOCD
sudo cp ~/.local/stm32-gdbtest/xpack-openocd-0.12.0-7/openocd/contrib/60-openocd.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

The J-Link software for Linux (the `arm64` package for Orange Pi 5) is downloaded from
the SEGGER site after accepting the license and installed with
`sudo dpkg -i JLink_Linux_V…_arm64.deb`; the package installs `/opt/SEGGER/JLink` and
its own udev rules. Version 8.32 is verified on the Windows stands. After the
debuggers are connected, `doctor` shows the devices found, their serial numbers and
access to `/dev/bus/usb`.

ST-LINK GDB Server (STM32CubeCLT) is not released for aarch64: on Orange Pi 5 use the
`openocd` and `jlink` backends. All three are available on Linux x86_64.

## Local stand and runs

Copy a template from `Tests/firmware/stands/*.example.toml` to `*.local.toml` (such
files are not committed) and set the serial shown by `doctor`. For OpenOCD
`executable = "openocd"` is enough — it comes from the environment's `PATH`; for
J-Link use `executable = "/opt/SEGGER/JLink/JLinkGDBServerCLExe"`.

```sh
. ~/.local/stm32-gdbtest/env.sh
python3 -B -m stm32_gdbtest doctor --stand Tests/firmware/stands/f411ce-openocd.local.toml
python3 -B Tests/firmware/run_hw.py --profile f411ce --stand Tests/firmware/stands/f411ce-openocd.local.toml
```

`run_hw.py` reprograms Flash; the result is `build/hw/<profile>-<stand>/summary.json`
([checks and CI](testing.md)). Your own project uses the same environment: the CMake
integration finds `arm-none-eabi-gdb-py3` on `PATH`.

## Lock and processes

The debugger is protected by an `flock` file in `/tmp/stm32-gdbtest-locks` (or in
`STM32_GDBTEST_LOCK_DIR`) shared by all users and projects of the host. The server and
GDB run in their own process group and stop together with their children. Details and
behaviour after a crash: [debugger ownership](DEBUGGER_OWNERSHIP.md#linux).

## WSL2 and usbipd-win

A debugger can be forwarded into a WSL2 distribution (`usbipd bind` and
`usbipd attach --wsl` on Windows); after that the steps are the same as on Linux. The
WSL lock does not interact with the Windows mutex, so one debugger must not be used
from Windows and WSL at the same time. This scenario has not been checked on hardware
yet (question 11.2.20 of the specification).

## Limits

- Installation, host tests, `doctor`, build and preparation are checked in CI (the
  `linux-stand` job, Ubuntu 20.04 x86_64 and aarch64). Hardware results on Orange Pi 5
  go to the [status](STATUS.md) after the run.
- A crash of the runner does not stop the server's process group: check
  `pgrep -a openocd` and `pgrep -a JLink` before retrying.
- J-Link STLink (the Nucleo on-board ST-Link reflashed to J-Link) on Orange Pi 5 takes
  about 10 s to connect to the target — longer than the default server readiness
  limit. Set `startup_timeout_s = 30` in the stand of such a debugger. The cause of the
  delay is not known; J-Link CE and ST-Link through OpenOCD connect in a fraction of a second.
- xPack OpenOCD 0.12.0-7 warns about the deprecated `tcl_port`, `telnet_port`,
  `gdb_port`; the commands stay compatible with OpenOCD 0.12.0.
