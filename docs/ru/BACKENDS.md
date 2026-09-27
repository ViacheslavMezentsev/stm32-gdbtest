# GDB-серверы (backend)

[Документация](index.md) → GDB-серверы · [English](../en/BACKENDS.md)

Backend задаёт запуск и готовность сервера, команды setup, reset, завершения и
восстановления. Сценарии пользуются общим Target API; ожидания периферии остаются
у потребителя. Стенд выбирается `--stand` → `STM32_GDBTEST_STAND` → `session.stand`
([API](API.md)). Аппаратный запуск поддерживается на Windows.

## Стенд

Таблица `[probe]` локального TOML:

| Ключ | Значение |
| --- | --- |
| `backend` | `openocd`, `stlink` (ST-LINK GDB Server) или `jlink` |
| `serial` | Явный серийный номер отладчика; для J-Link — десятичный USB-номер |
| `executable` | Сервер: имя в PATH или абсолютный путь |
| `speed_khz` | 1…4000, по умолчанию 1000 — верхний предел, не фактическая частота |
| `flash` | `if-different` (по умолчанию) или `verify-only` |
| `programmer_dir` | Только `stlink`: абсолютный каталог с `STM32_Programmer_CLI.exe` |

Неизвестный ключ отклоняется. Шаблоны: [OpenOCD](../../examples/stands/stlink.example.toml)
и [OpenOCD, ST, J-Link для CI-прошивок](../../Tests/firmware/stands/jlink.example.toml)
(в той же папке `openocd.example.toml` и `stlink.example.toml`). Локальные пути и
серийные номера не коммитятся (`*.local.toml`). `run --prepare-only --stand …`
проверяет стенд и команды backend без подключения к отладчику.

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
`STM32F030R8T6` → `STM32F030R8` (встроенный J-Link STLink на Nucleo). Другие MCU
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
