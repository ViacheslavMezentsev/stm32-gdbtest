# MMIO on an instrumented Renode peripheral / MMIO в Renode

This fixture exercises public `Target.mmio` with the captured SVD configuration,
a real GDB remote connection and an independent PythonPeripheral access journal.
It uses the external diagnostic launcher because the production Renode backend
intentionally disallows arbitrary Python peripheral scripts in platform files.
No physical board is used. This is a transport regression, not a board model.

Фикстура проверяет публичный `Target.mmio` с захваченным SVD, настоящим GDB и
независимым журналом обращений PythonPeripheral. Внешний диагностический launcher
нужен потому, что штатный backend намеренно запрещает произвольные Python-модели
в платформе. Это транспортная регрессия, а не модель конкретной платы.

Run from the repository root / Из корня репозитория:

```powershell
python tests/mmio-renode/run.py --toolchain "$HOME/xpack-arm-none-eabi-gcc-14.2.1-1.1" --renode "C:/Program Files/Renode/renode.exe"
```

```sh
python3 tests/mmio-renode/run.py --toolchain /opt/xpack-arm-none-eabi-gcc-14.2.1-1.1 --renode /opt/renode-1.17.0/renode
```

Requires Renode 1.17 and a GDB build with Python and RemoteTargetConnection.send_packet.
Artifacts: `build/mmio-renode/<run>/`, including ELF, input hashes, versions,
callback log, scenario observations and result JSON. Deliberately incorrect SVD
is a negative control: the independent oracle must detect the destructive read.
The simulated lost ACK occurs after a real write; exactly one callback is required.

Нужны Renode 1.17 и GDB с Python/RemoteTargetConnection.send_packet. Артефакты:
`build/mmio-renode/<run>/`: ELF, хеши входов, версии, журнал callbacks, наблюдения
и result.json. Неверный SVD — отрицательный контроль: независимая проверка обязана
заметить разрушительное чтение. Потеря ACK имитируется после настоящей записи;
допустим ровно один callback.

See [RU contract](../../docs/ru/api/mmio.md) / [EN contract](../../docs/en/api/mmio.md).
