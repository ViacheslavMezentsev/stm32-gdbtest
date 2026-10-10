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
| `backend` | `openocd`, `stlink` (ST-LINK GDB Server), `st-util` или `jlink` |
| `serial` | Явный серийный номер отладчика; для J-Link — десятичный USB-номер |
| `executable` | Сервер: имя в PATH или абсолютный путь; по умолчанию `openocd`, `ST-LINK_gdbserver(.exe)`, `st-util(.exe)`, `JLinkGDBServerCL.exe` (Windows) или `JLinkGDBServerCLExe` (Linux) |
| `speed_khz` | 1…4000, по умолчанию 1000 — верхний предел, не фактическая частота |
| `flash` | `if-different` (по умолчанию) или `verify-only` |
| `[remote]` | Отдельная таблица: GDB-сервер на хосте стенда Linux по SSH ([Linux-стенд](LINUX_STAND.md#удалённый-gdb-сервер-windows-или-wsl--orange-pi)); `executable` и `programmer_dir` тогда относятся к хосту стенда |
| `startup_timeout_s` | 1…120, по умолчанию 10 — сколько ждать готовности сервера; больше нужно отладчикам с медленным подключением к цели |
| `programmer_dir` | Только `stlink`: абсолютный каталог с `STM32_Programmer_CLI.exe` (на Linux — без `.exe`) |
| `interface` | `openocd`: скрипт интерфейса, по умолчанию `interface/stlink.cfg`; `jlink`: `SWD` (по умолчанию) или `JTAG` |
| `transport` | Только `openocd`: `transport select …` после скрипта интерфейса (`swd`, `jtag`, `hla_swd`, `hla_jtag`, `dapdirect_swd`, `dapdirect_jtag`, `sdi`); по умолчанию не задаётся |

Неизвестный ключ отклоняется. Шаблоны: [OpenOCD](../../examples/stands/stlink.example.toml)
и [OpenOCD, ST, st-util, J-Link для CI-прошивок](../../tests/firmware/stands/jlink.example.toml)
(в той же папке `openocd.example.toml`, `stlink.example.toml`, `st-util.example.toml` и `remote.example.toml` для
удалённого стенда). В локальных путях (`executable`, `programmer_dir`, `identity_file`)
раскрываются `~`, `%VAR%` и `$VAR`: `%USERPROFILE%/...` вместо личного пути. Локальные пути и
серийные номера не коммитятся: локальный стенд — `<профиль>-<backend>.local.toml`, удалённый —
`<профиль>-<backend>.remote.toml`, оба исключены из Git. `run --prepare-only --stand …`
проверяет стенд и команды backend без подключения к отладчику, а `doctor --stand …`
дополнительно проверяет GDB-Python, OpenOCD/st-util и доступ к USB.

Профиль `target.toml` может назвать устройство J-Link ключом `jlink_device` (например, для МК вне проверенных
STM32); без него используется таблица проверенных STM32. Диалект каждого сервера задаётся секцией профиля
схемы 2: `[openocd]` (в том числе `reset_halt = "monitor reset init"` — сброс с процедурой инициализации
цели), `[jlink]`, `[stlink]`, `[st-util]`. Секция необязательна: без неё действует встроенный диалект сервера. Блокировка
отладчика различает семейство зонда: другой скрипт интерфейса OpenOCD не делит блокировку с ST-Link того же
серийного номера.

На Linux ST-LINK GDB Server (STM32CubeCLT) есть только для x86_64; на aarch64
(Orange Pi 5) используются OpenOCD, J-Link и st-util. OpenOCD 0.10 из репозитория Ubuntu 20.04
не содержит `interface/stlink.cfg`, поэтому окружение стенда ставит xPack OpenOCD
0.12.0-7. Эта сборка предупреждает об устаревших `tcl_port`/`telnet_port`/`gdb_port`;
команды оставлены совместимыми с OpenOCD 0.12.0.

## TOML

| Файл | Назначение | Связь с backend |
| --- | --- | --- |
| `session.toml` | Конфигурация сессии; `[config]` ссылается на файлы относительно её каталога | Не выбирает исполняемый файл сервера |
| `target.toml` | MCU, память, identity и диалекты schema 2 | `[openocd]`, `[stlink]`, `[jlink]`, `[st-util]`; необязательные секции |
| `api.toml` | Параметры API сценариев и пользовательские данные | Прежний `reset.command` удалён; команды сервера здесь не задаются |
| `full_image.toml` | Необязательная политика полного образа | Одинаковая проверка образа для всех backend, см. [образы](IMAGES.md) |
| `<profile>-<backend>.local.toml` / `.remote.toml` | `[probe]` выбирает сервер, serial и параметры; `[remote]` включает SSH | Локальный файл стенда вне Git, выбран через `--stand` или описанный выше приоритет |
| `session.json` | Сгенерированные входы runner, ELF и сборки | Не заменяет пользовательский session.toml; вручную не редактируется |

```toml
# session.toml; these are file references, not backend commands.
[config]
target = "target.toml"
api = "api.toml"
image = "full_image.toml" # Optional; omit when not using a full-image policy.
```

Полный пример подключения `SESSION_CONFIG`, генерация session.json и CLI — [API](API.md).
Профиль не выбирает backend: выбор делает файл стенда. Разделы target в отдельных страницах —
фрагменты полного профиля, а не самостоятельные target.toml. `reset_run` допустим только у OpenOCD;
завершение других серверов задаёт backend. Разовый `STM32_GDBTEST_RESET_COMMAND` меняет reset/halt,
но не recovery; это не замена переносимой конфигурации профиля.

## Проверенные различия

| Backend / подробности | Готовность | Reset/halt по умолчанию | Завершение и recovery |
| --- | --- | --- | --- |
| [OpenOCD](backends/openocd.md) | Listening on port … for gdb connections | `monitor reset halt` | `monitor reset run`, `disconnect` |
| [ST-LINK GDB Server](backends/stlink.md) | Waiting for debugger connection | `monitor reset` | `monitor reset`, `detach` |
| [J-Link](backends/jlink.md) | Waiting for GDB connection | `monitor reset` | `monitor reset`, `monitor go`, `disconnect` |
| [st-util](backends/st-util.md) | Listening at *:PORT… (ASCII `...`) | `monitor reset` | `monitor reset`, `monitor resume`, `disconnect` |

Все используют `target extended-remote`. Схема 1 сохраняется для совместимости: верхнеуровневые
reset-поля действуют только для OpenOCD. Номера схем и миграция — [API](API.md).

## Особенности серверов

Отдельные страницы содержат TOML, зависимости, запуск, завершение, причины исправлений и ограничения.
Для st-util дополнительно приведены результаты 1.6.0/1.9.0 и сборка 1.9.0 с частной libusb на Ubuntu 20.04.
Приёмка относится к конкретным версиям и стендам — [матрица](API_ACCEPTANCE.md).

## Ограничения и расширение

Vendor server может обратиться к SWD при старте до клиента GDB. `prepare-only` не запускает сервер;
успех doctor не подтверждает MCU или сценарий. Приёмка нового backend включает запись/verify-only,
timeout/recovery, завершение и конечное состояние MCU. Команды monitor нельзя переносить по аналогии.
Mass erase, option bytes, firmware отладчика и shared mode автоматически не включаются.
Наблюдение без остановки, SWV, external loaders, multicore и authentication не входят в проверенный общий API.
[Владение отладчиком](DEBUGGER_OWNERSHIP.md) · [Linux/SSH](LINUX_STAND.md) · [Памятка](HOWTO.md).

## st-util (v0.4.0)

Подробности перенесены на [страницу st-util](backends/st-util.md), включая различия версий,
сборку Ubuntu 20.04, ожидание Listening/idle и фактический код завершения.
