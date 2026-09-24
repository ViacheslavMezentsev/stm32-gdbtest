# Backend GDB-серверов

Backend задаёт запуск/готовность, setup/reset/finish/recovery. Сценарии пользуются
общим Target API; ожидания периферии остаются у потребителя. Stand TOML выбирается
CLI --stand → STM32_GDBTEST_STAND → session.stand. См. [API](API.md).

В секции [probe]: backend=openocd|stlink|jlink, явный serial, executable,
speed_khz (1..4000), flash=if-different|verify-only. ST дополнительно требует
programmer_dir с STM32_Programmer_CLI.exe. J-Link serial — десятичный USB-номер.
Шаблон: [OpenOCD](../examples/stands/stlink.example.toml); локальные пути/serial не коммитить.

## Проверенные различия

| Операция | OpenOCD 0.12.0 | ST-LINK GDB Server 7.14.0 (CubeCLT 1.22.0) |
| --- | --- | --- |
| Выбор MCU | target/stm32f1x.cfg | Определение сервером ST; identity guard раннера сохраняется |
| Запуск | ST-Link interface + target; localhost | SWD, attach `-g`, persistent `-e`, serial, CubeProgrammer path |
| Готовность | Listening on port … for gdb connections | Waiting for debugger connection |
| Подключение GDB | extended-remote | extended-remote |
| Reset/halt | monitor reset halt | monitor reset |
| Прошивка | GDB load, OpenOCD flash driver | GDB load, сервер вызывает CubeProgrammer |
| Проверка образа | Чтение Flash до/после записи | То же; дополнительно включён серверный verify `-s` |
| Завершение | monitor reset run; disconnect | monitor reset; detach (возобновляет выполнение) |
| Внешний timeout | Новый GDB-клиент для recovery | Новый клиент к persistent-серверу; reset + detach |
| Runtime metadata | Версия OpenOCD, STLINK firmware/API | Версия ST server и firmware; API v2 баннером не сообщается, поле null |

Schema 1 target.toml сохранена ради совместимости: её openocd_target/reset-поля
использует только OpenOCD. ST получает команды из backend, а MCU identity,
Flash bounds, breakpoints и fault handlers — из общего профиля. Это промежуточная
совместимость, не универсальная новая схема профиля для всех серверов.

Сервер ST сам устанавливает аппаратное соединение до запуска клиента GDB.
Runtime-проверка GDB API выполняется до подключения GDB/reset/load, но не является проверкой
до любого обращения сервера к SWD. Attach не означает отсутствие влияния отладчика.
При запросе 1000 kHz ST сообщил COM frequency 950 kHz; запрошенная частота — предел,
а не доказательство фактической частоты интерфейса.

Сервер ST открывает дополнительный порт для SWV (наблюдался GDB port + 1).
В установленной CLI-справке нет аналога OpenOCD bindto; эти процессы предназначены
для локального стенда. SWV в текущие тесты не включён. Shared mode `-t` не используется:
доступ обоих backend защищён одной блокировкой по serial, сервер принадлежит запуску.
Все logs/temp/CubeProgrammer-временные файлы направляются в проект потребителя: cwd запуска,
`--temp-path`, `-f`, TEMP/TMP. После завершения дерево процессов закрывается.


## J-Link

Реализованы и проверены mappings STM32F103C8T6 → STM32F103C8 и
STM32F030R8T6 → STM32F030R8 (Nucleo с J-Link STLink, V8.32, SWD). Другие MCU отклоняются
до запуска сервера, пока mapping не проверен. SWD, явный USB serial, localhost;
SWO/Telnet/RTT-порты выключены. Setup отключает Flash breakpoints. Reset/halt:
monitor reset; finish: monitor reset, monitor go, disconnect. Используются hardware BP.

## Ограничения и расширение

Vendor server может обращаться к SWD уже при старте. Offline ELF preflight идёт
до сервера; runtime API presence check не означает отсутствие аппаратного доступа.
Нельзя переносить monitor/detach между серверами по аналогии. Новый backend требует
проверки Flash, verify-only, timeout/recovery и конечного состояния MCU.
Mass erase, option bytes, обновление firmware и shared mode автоматически не включаются.
Блокировки: [DEBUGGER_OWNERSHIP](DEBUGGER_OWNERSHIP.md).
Наблюдение без halt, SWV, внешние loaders, multicore и authentication не входят
в доказанный общий API. observe_sleep и опыт Commander — инструменты стендового проекта.

[Команды и результаты стендов](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/GDB_BACKENDS.md), [опыты J-Link](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/JLINK.md).
