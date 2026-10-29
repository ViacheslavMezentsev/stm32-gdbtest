# QEMU: native local backend

[Documentation](../../en/index.md) → [Backends](BACKENDS.md) · [Русский](../ru/QEMU.md)

For 0.5.0: each scenario owns a fresh QEMU process. The initial supported machine is
`netduinoplus2` (Cortex-M4). This limited board model does not represent every STM32
with that core. Emulator PASS does not establish physical MCU behavior.

## Configuration

[Stand example](../../../tests/qemu-backend/stand.example.toml):

```toml
schema = 1
[emulator]
backend = "qemu"
executable = "qemu-system-arm"
startup_timeout_s = 15
shutdown_timeout_s = 5
[qemu]
machine = "netduinoplus2"
semihosting = false
```

`executable` is a PATH name or path; timeouts are positive numbers up to 60 seconds.
Only `netduinoplus2` is accepted; unknown settings are rejected.
Target uses [schema 3](../../../tests/qemu-backend/target.toml),
`environment="emulator"`, `architecture="cortex-m"`, without hardware identity.
Hardware schemas 1/2 remain supported. See [Renode](RENODE.md) for schema 3 fields.
Probe, SSH, attach, keep, extra arguments and other machines are unsupported.

Semihosting defaults to false. Enabling it selects `enable=on,target=native`:
it executes trusted firmware requests on the host, including file operations;
it is not firmware isolation. Diagnostic output is retained in `server.log`.
The serial port goes to `uart.log`; file existence does not establish model UART behavior.

## Lifecycle and evidence

Runner snapshots ELF, starts QEMU with `-S`, `-no-reboot`, no GUI/monitor and GDB
bound to `127.0.0.1`. The TCP probe only establishes port readiness; GDB then checks
the halted target, a single CPU thread and file-backed Flash LOAD sections.
Execution subsequently reaches main. RAM/BSS are not claimed as verified ELF bytes.
Full Flash programming and hardware identity expectations do not apply.

Results include `mode="emulator"`, `environment="emulator"`, `hardware_accessed=false`,
QEMU version, machine and semihosting option. The model is built into QEMU;
there is no separate REPL/model hash. Normal capture=true enables `records.json`.
Timeouts use host time, not MCU virtual time.
Completion, FAIL, ERROR and timeout clean owned processes and verify port closure.
Cleanup failure produces ERROR while preserving the previous outcome.
`reset()` refuses before a command (`unsupported_backend/validation/none`). Start a
new scenario for clean state. Arbitrary `execute()` is outside these guarantees.

## Reproducible check

```powershell
python tests/qemu-backend/run.py --toolchain "$env:STM32_TOOLCHAIN_PATH" --qemu qemu-system-arm
```

Use the same command with Linux paths on Linux. It builds a neutral ELF and creates
unique `build/qemu-backend/<timestamp>/` artifacts: prepare, PASS, deliberate FAIL,
reset refusal, timeout, repeat PASS, early server exit and real semihosting output.
`summary.json` validates seven expected outcomes; FAIL/ERROR artifacts are retained.
Use its `session.json` with normal `run --session ... --test HW_EMU_STARTUP`.
`doctor --stand ...` checks version and machine availability without firmware/USB access.

Validation pair: Windows QEMU 11.1.0, Linux QEMU 11.0.0; GCC 14.2.1/GDB-Python.
Retain version and model when comparing DDTT evidence.
Model selection and offline build methodology follow
[stm32-cmake-yml](https://github.com/ViacheslavMezentsev/stm32-cmake-yml/tree/main/tools/qemu).
Linux checks reuse an existing image with sources and builds in a fresh volume;
[local CI](local-ci.md). ELF loading does not establish peripheral model completeness.
