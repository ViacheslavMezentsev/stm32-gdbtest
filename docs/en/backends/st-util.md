# st-util

[Backend](index.md) · [Русский](../../ru/backends/st-util.md)

Open-source GDB server from [stlink](https://github.com/stlink-org/stlink), backend `st-util`.
This is distinct from ST-LINK GDB Server; CubeProgrammer is not required. Windows/Scoop and
Ubuntu 20.04/aarch64 on OrangePi were checked. The [matrix](../API_ACCEPTANCE.md) defines acceptance boundaries.

## Two versions encountered

| Version | Observation | Module conclusion |
| --- | --- | --- |
| Ubuntu `stlink-tools` 1.6.0+ds-1, `st-util v1.6.0` | Lacks the selected `--freq`; a local experiment needed different serial encoding. Three F030 repeated reach/resume/stepi variants did not advance ticks as expected | Not accepted. No 1.6.0 workaround in the public backend; doctor printing its version does not establish runtime compatibility |
| `st-util v1.9.0`, source `0697e5668df5f4f191c4d9f11803d5e995eb90df`, libusb 1.0.27 | The same three navigation checks and BOOT/GPIO passed; after lifecycle fixes all five STM32 full suites passed over SSH | Verified combination for this stand, not a promise for every binary reporting 1.9.0 |

The 1.6.0 experiment used system libusb 1.0.23. Selected 1.9.0 needed at least 1.0.24; a separate 1.0.27
was installed. Server, library and arguments changed together: the causal role of a single IRQ/step
fix was not isolated. Scenario expectations were not relaxed to obtain PASS.

## TOML and commands

[TOML map](../BACKENDS.md#toml) · [stand template](../../../tests/firmware/stands/st-util.example.toml).
Replace placeholders in `<profile>-st-util.remote.toml`; `executable` is an absolute path **on the stand host**.
Replace `stand-user` inside the path too. Local operation omits `[remote]`.

```toml
[probe]
backend = "st-util"
serial = "REPLACE_WITH_24_HEX_DIGITS"
executable = "/home/stand-user/.local/stm32-gdbtest/stlink-1.9.0/bin/st-util"
speed_khz = 1000
flash = "if-different"
startup_timeout_s = 10

[remote]
host = "stand-host"
user = "stand-user"
identity_file = "~/.ssh/id_ed25519_stand"
```

Windows can use `%USERPROFILE%/scoop/apps/stlink/current/bin/st-util.exe`. Serial is 24 hex digits,
passed uppercase, not a device index. Target schema 2 fragment (a complete MCU profile is still required):

```toml
[st-util]
reset_halt = "monitor reset"
```

The section is optional; `reset_run` is rejected. Setup: `set mem inaccessible-by-default off`;
finish/recovery: `monitor reset`, `monitor resume`, `disconnect`. Do not copy ST/OpenOCD commands here.
Launch: `--multi --no-reset --serial SERIAL --freq 1000k --listen_port PORT`. Runner allocates the port;
do not start a second server on the same probe. `--multi` permits a recovery client, not shared concurrent tests.
ST-Link locks are shared with OpenOCD and ST's server. The server listens on all network interfaces;
`[remote]` uses the module's SSH tunnel, not `st-server`/`--remote`.

## Building 1.9.0 on Ubuntu 20.04

The recipe reproduces the installed and tested OrangePi build settings; commands were consolidated
from source/CMakeCache, not executed again here. Build natively, not with arm-none-eabi:
GCC with C17, CMake≥3.21 (tested 3.28.3), libusb≥1.0.24. System CMake 3.16/libusb 1.0.23 are insufficient.
First install the [stand environment](../LINUX_STAND.md) that supplies `env.sh`.
GUI is unnecessary; this example assumes a headless stand without GTK development packages.

System `/usr/bin/st-util` and libusb stay installed. The build installs without sudo into user prefixes;
if a prefix already holds a used build, preserve it first or choose different prefixes. Do not reinstall
libraries while a hardware test is running.

```bash
# On the Ubuntu 20.04 stand; prerequisite packages need administrator rights.
sudo apt update
sudo apt install build-essential pkg-config libudev-dev git curl bzip2
```

```bash
(
set -eu
# Install the module's Linux stand environment first (CMake 3.28.3 in our checks).
. "$HOME/.local/stm32-gdbtest/env.sh"
cmake --version
gcc --version

backend_prefix="$HOME/.local/stm32-gdbtest/stlink-1.9.0"
usb_prefix="$HOME/.local/stm32-gdbtest/libusb-1.0.27"
source_dir="$(mktemp -d "$HOME/stlink-build.XXXXXX")"
cd "$source_dir"

curl --fail --location --output libusb-1.0.27.tar.bz2 \
  https://github.com/libusb/libusb/releases/download/v1.0.27/libusb-1.0.27.tar.bz2
printf '%s  %s\n' \
  fffaa41d741a8a3bee244ac8e54a72ea05bf2879663c098c82fc5757853441575 \
  libusb-1.0.27.tar.bz2 | sha256sum --check -
tar -xf libusb-1.0.27.tar.bz2
(
  cd libusb-1.0.27
  ./configure --prefix="$usb_prefix" --libdir="$usb_prefix/lib" --disable-static
  make -j2
  make install
)

git clone https://github.com/stlink-org/stlink.git stlink
# Exact source revision of the tested 1.9.0 build, not a floating branch.
git -C stlink checkout --detach 0697e5668df5f4f191c4d9f11803d5e995eb90df
git -C stlink rev-parse HEAD
export PKG_CONFIG_PATH="$usb_prefix/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
pkg-config --modversion libusb-1.0

cmake -S stlink -B stlink-build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$backend_prefix" \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DLIBUSB_INCLUDE_DIR="$usb_prefix/include/libusb-1.0" \
  -DLIBUSB_LIBRARY="$usb_prefix/lib/libusb-1.0.so" \
  -DCMAKE_INSTALL_RPATH="$backend_prefix/lib;$usb_prefix/lib" \
  -DSTLINK_MODPROBED_DIR="$backend_prefix/share/modprobe.d" \
  -DSTLINK_UDEV_RULES_DIR="$backend_prefix/share/udev/rules.d"
cmake --build stlink-build --parallel 2
cmake --install stlink-build

"$backend_prefix/bin/st-util" --version
ldd "$backend_prefix/bin/st-util"
ldd "$backend_prefix/lib/libstlink.so.1"
sha256sum "$backend_prefix/bin/st-util" "$backend_prefix/lib/libstlink.so.1" \
  "$usb_prefix/lib/libusb-1.0.so.0"
printf 'Sources and build logs: %s\n' "$source_dir"
)
```


Use the libusb release `.tar.bz2` with generated `configure`, not GitHub's automatic source zip/tar.gz.
[Upstream explanation](https://github.com/libusb/libusb/releases/tag/v1.0.27).
Selected stlink revision: [CMakeLists](https://github.com/stlink-org/stlink/blob/0697e5668df5f4f191c4d9f11803d5e995eb90df/CMakeLists.txt).

`ldd` must resolve libstlink from the stlink 1.9.0 prefix and libusb from the 1.0.27 prefix, without `not found`.
Check libstlink too: dependencies can be transitive. `st-util --version` alone is insufficient.
`PKG_CONFIG_PATH` and explicit LIBUSB paths avoid old headers/libraries; RPATH runs the selected binary
without globally replacing `LD_LIBRARY_PATH` or system libusb.

STLINK_UDEV_RULES_DIR/STLINK_MODPROBED_DIR prevent `cmake --install` writing into `/lib/udev/rules.d`
and `/etc/modprobe.d`. These are saved files only: user-prefix rules do not become active automatically.
USB permissions were already configured on our stand. On a new stand the administrator configures
[udev/access](../LINUX_STAND.md) and reconnects USB outside testing. Running the runner under sudo is not
a substitute for permissions. `tools/linux_stand.py` does not install st-util yet.

## Observations that required module changes

| Observation | Change and boundary |
| --- | --- |
| The 1.9.0 memory map omitted F411 factory register `0x1FFF7A22` | Setup permits GDB reads outside the map; identity, Flash-size and image verification remain enabled |
| After external timeout the server was not ready for recovery | Wait for a new complete `Listening at *:PORT...` after the last `GDB connected.`; the initial startup marker is insufficient |
| Real Listening ends with an ellipsis | Parser accepts both forms, but only complete lines for the current port/attempt |
| F103 libusb assertion at shutdown; helper could hide a late server exit | Wait for idle before termination, reap before publishing actual exit; retain the original outcome as `status_before_cleanup` |
| A missing SSH reader could block helper output | Bounded nonblocking output and local idle observation; lost confirmation remains ERROR |
| A long ADC matrix over SSH took about 60s | Specific F4 scenarios received 120s; assertions and the global timeout were not relaxed |

Recovery idle: up to 5s, one recovery attempt: up to 10s; shutdown idle: up to 5s. Helper observes idle
locally even on SSH loss, then TERM 3s, KILL 5s, reap 5s; runner waits up to 25s for SSH.
Normal remote st-util completion requires actual exit 0 and confirmed idle. Unknown exit, SIGKILL,
heartbeat timeout or a missing marker means ERROR. This is bounded cleanup, not proof of USB safety
under every failure.

## Installation checks and failure diagnosis

Order: `--version`/`ldd` → `doctor --stand …` → `run --prepare-only` → BOOT/GPIO →
timeout/recovery lifecycle → full suite on an agreed board. CLI and generated session.json:
[API](../API.md). Build success does not establish HW PASS.

Preserve `server.log`, `tunnel.log`, `gdb.log`, `recovery.log` and `result.json` together.
`cannot recv: -2` occurred at disconnect followed by Listening/exit 0, but is not universally harmless.
Check phase, actual exit, idle and the next connection. Empty/binary USB serial can produce a doctor WARN;
use `python -X utf8` for Windows capture. After USB ERROR preserve the failure, inspect processes/lock
and restore only once access returns.
