# Renode runner example

[Русский](../../docs/ru/RENODE.md) · [English](../../docs/en/RENODE.md)


```sh
python tests/renode-backend/run.py --toolchain /opt/xpack-arm-none-eabi-gcc-14.2.1-1.1 --renode /opt/renode-1.17.0/renode
```

The same command accepts Windows paths. Uses gdb-py3, a fresh neutral ELF and owned
Renode processes. Results and separate attempts are saved under build/renode-backend.
Intentional FAIL/ERROR/SKIP are checked against expectations; summary.json must contain
only ok=true. The live scenarios use the public runner, not a separate probe launcher.
See [RU](../../docs/ru/LIVE_EXECUTION.md) / [EN](../../docs/en/LIVE_EXECUTION.md).
