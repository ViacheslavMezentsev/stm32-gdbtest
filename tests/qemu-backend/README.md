# QEMU runner example

[Русский](../../docs/guides/ru/QEMU.md) · [English](../../docs/guides/en/QEMU.md)

`run.py` builds a Cortex-M4 ELF and checks seven expected outcomes with the real runner.
Shared scenarios and linker script come from `../renode-backend`; no hardware is accessed.
Artifacts stay in a unique `build/qemu-backend/` directory.
