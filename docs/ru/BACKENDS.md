# GDB-серверы (backend)

[Документация](index.md) → GDB-серверы · [English](../en/BACKENDS.md)

Backend задаёт запуск и готовность сервера, команды setup, reset, завершения и
восстановления. Сценарии пользуются общим Target API; ожидания периферии остаются
у потребителя. Стенд выбирается `--stand` → `STM32_GDBTEST_STAND` → `session.stand`
([API](API.md)). Аппаратный запуск поддерживается на Windows и Linux
([Linux-стенд](LINUX_STAND.md)).

## Стенд

Таблица `[probe]` локального TOML:

| Ключ | Значение |
| --- | --- |
| `backend` | `openocd`, `stlink` (ST-LINK GDB Server) или `jlink` |
| `serial` | Явный серийный номер отладчика; для J-Link — десятичный USB-номер |
| `executable` | Сервер: имя в PATH или абсолютный путь; по умолчанию `openocd`, `ST-LINK_gdbserver(.exe)`, `JLinkGDBServerCL.exe` (Windows) или `JLinkGDBServerCLExe` (Linux) |
| `speed_khz` | 1…4000, по умолчанию 1000 — верхний предел, не фактическая частота |
| `flash` | `if-different` (по умолчанию) или `verify-only` |
| `[remote]` | Отдельная таблица: GDB-сервер на хосте стенда Linux по SSH ([Linux-стенд](LINUX_STAND.md#удалённый-gdb-сервер-windows-или-wsl--orange-pi)); `executable` и `programmer_dir` тогда относятся к хосту стенда |
| `startup_timeout_s` | 1…120, по умолчанию 10 — сколько ждать готовности сервера; больше нужно отладчикам с медленным подключением к цели |
| `programmer_dir` | Только `stlink`: абсолютный каталог с `STM32_Programmer_CLI.exe` (на Linux — без `.exe`) |
| `interface` | `openocd`: скрипт интерфейса, по умолчанию `interface/stlink.cfg`; `jlink`: `SWD` (по умолчанию) или `JTAG` |
| `transport` | Только `openocd`: `transport select …` после скрипта интерфейса (`swd`, `jtag`, `hla_swd`, `hla_jtag`, `dapdirect_swd`, `dapdirect_jtag`, `sdi`); по умолчанию не задаётся |

Неизвестный ключ отклоняется. Шаблоны: [OpenOCD](../../examples/stands/stlink.example.toml)
и [OpenOCD, ST, J-Link для CI-прошивок](../../tests/firmware/stands/jlink.example.toml)
(в той же папке `openocd.example.toml`, `stlink.example.toml` и `remote.example.toml` для
удалённого стенда). В локальных путях (`executable`, `programmer_dir`, `identity_file`)
раскрываются `~`, `%VAR%` и `$VAR`: `%USERPROFILE%/...` вместо личного пути. Локальные пути и
серийные номера не коммитятся: локальный стенд — `<профиль>-<backend>.local.toml`, удалённый —
`<профиль>-<backend>.remote.toml`, оба исключены из Git. `run --prepare-only --stand …`
проверяет стенд и команды backend без подключения к отладчику, а `doctor --stand …`
дополнительно проверяет GDB-Python, OpenOCD и доступ к USB.

Профиль `target.toml` может назвать устройство J-Link ключом `jlink_device` (например, для МК вне проверенных
STM32); без него используется таблица проверенных STM32. Для OpenOCD профиль допускает `reset_halt =
"monitor reset init"` — сброс с процедурой инициализации цели. Блокировка отладчика различает семейство зонда:
другой скрипт интерфейса OpenOCD не делит блокировку с ST-Link того же серийного номера.

На Linux ST-LINK GDB Server (STM32CubeCLT) есть только для x86_64; на aarch64
(Orange Pi 5) используются OpenOCD и J-Link. OpenOCD 0.10 из репозитория Ubuntu 20.04
не содержит `interface/stlink.cfg`, поэтому окружение стенда ставит xPack OpenOCD
0.12.0-7. Эта сборка предупреждает об устаревших `tcl_port`/`telnet_port`/`gdb_port`;
команды оставлены совместимыми с OpenOCD 0.12.0.

## Проверенные различия

| Операция | OpenOCD 0.12.0 | ST-LINK GDB Server 7.14.0 (CubeCLT 1.22.0) | J-Link GDB Server 8.32 |
| --- | --- | --- | --- |
| Выбор MCU | `openocd_target` профиля | Определяет сервер ST; identity runner сохраняется | Mapping MCU → устройство J-Link |
| Запуск | `interface/stlink.cfg` + target, localhost | SWD, attach `-g`, persistent `-e`, serial, путь CubeProgrammer | SWD, `-USB <serial>`, localhost, без SWO/Telnet/RTT |
| Готовность | `Listening on port … for gdb connections` | `Waiting for debugger connection` | `Waiting for GDB connection` |
| Подключение GDB | extended-remote | extended-remote | extended-remote |
| Setup | — | — | `monitor flash breakpoints = 0` |
| Reset/halt | `monitor reset halt` | `monitor reset` | `monitor reset` |
| Запись | GDB load, flash driver OpenOCD | GDB load, сервер вызывает CubeProgrammer; серверный verify `-s` | GDB load |
| Завершение | `monitor reset run`, `disconnect` | `monitor reset`, `detach` | `monitor reset`, `monitor go`, `disconnect` |
| Внешний timeout | Новый GDB-клиент для recovery | Новый клиент к persistent-серверу: reset + detach | Новый клиент: reset + go + disconnect |
| Runtime metadata | Версия OpenOCD, firmware и API STLINK | Версия сервера и firmware; API v2 баннером не сообщается (`null`) | Версия сервера и строка firmware J-Link |

Все три backend на коммите `fbc103d` прошли одинаковый набор шагов CI-прошивок на
оборудовании, включая полный образ и timeout с восстановлением
([текущее состояние](STATUS.md)).

Schema 1 `target.toml` сохранена ради совместимости: поля `openocd_target`,
`reset_halt`, `reset_run` использует только OpenOCD. ST и J-Link получают команды
из backend, а identity, границы Flash, точки останова и fault handlers — из общего
профиля. Это промежуточная совместимость, не универсальная схема профиля.

## Особенности серверов

**ST-LINK GDB Server** сам устанавливает соединение по SWD до запуска клиента GDB:
проверка GDB API перед подключением не означает отсутствия обращения к отладчику.
Attach не означает отсутствия влияния отладчика. При запросе 1000 kHz сервер сообщал
COM frequency 950 kHz. Дополнительный порт SWV (наблюдался порт GDB + 1) в тестах
не используется; аналога OpenOCD `bindto` в справке нет, процессы рассчитаны на
локальный стенд. Shared mode `-t` не используется: оба ST-backend защищены одной
блокировкой по серийному номеру, сервер принадлежит запуску. Журналы и временные
файлы (`--temp-path`, `-f`, `TEMP`/`TMP`) направляются в каталог запуска потребителя;
после завершения дерево процессов закрывается.

**J-Link.** Проверены mappings `STM32F103C8T6` → `STM32F103C8` (J-Link CE) и
`STM32F030R8T6` → `STM32F030R8` (встроенный J-Link STLink на Nucleo); добавлен
`STM32F103CBT6` → `STM32F103CB` (WeAct BluePill-Plus, J-Link CE). Другие MCU
отклоняются до запуска сервера, пока mapping не проверен. Flash breakpoints
отключаются, используются аппаратные точки останова.

## Ограничения и расширение

- Vendor server может обращаться к SWD уже при старте. Offline-проверка ELF идёт
  до сервера, но проверка наличия GDB API не означает отсутствия аппаратного доступа.
- Команды monitor/detach нельзя переносить между серверами по аналогии. Новый backend
  или mapping требует проверки записи Flash, verify-only, timeout/recovery и конечного
  состояния MCU на оборудовании.
- Mass erase, option bytes, обновление прошивки отладчика и shared mode автоматически
  не включаются. Блокировки — [владение отладчиком](DEBUGGER_OWNERSHIP.md).
- Наблюдение без halt, SWV, внешние loaders, multicore и authentication не входят в
  доказанный общий API; `observe_sleep` и опыты с Commander — инструменты стендового проекта.

[Команды и результаты стендов](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/GDB_BACKENDS.md),
[опыты J-Link](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/JLINK.md).
