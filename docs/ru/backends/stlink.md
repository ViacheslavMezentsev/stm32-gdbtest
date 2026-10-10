# ST-LINK GDB Server

[Backend](index.md) · [English](../../en/backends/stlink.md)

Общие файлы сессии и параметры стенда — [карта TOML](../BACKENDS.md#toml). Фрагмент target дополняет полный профиль MCU.

## Настройка

Backend `stlink` — сервер ST из STM32CubeCLT, не открытый `st-util`. Для программирования нужен
STM32CubeProgrammer. На Windows проверены ST-LINK GDB Server 7.14.0 (CubeCLT 1.22.0) и 7.9.0.
У используемого CubeCLT Linux-сборка x86_64; для OrangePi/aarch64 применяйте OpenOCD или st-util.

```toml
[probe]
backend = "stlink"
serial = "REPLACE_WITH_STLINK_SERIAL"
executable = "C:/ST/STM32CubeCLT/STLink-gdb-server/bin/ST-LINK_gdbserver.exe"
programmer_dir = "C:/ST/STM32CubeCLT/STM32CubeProgrammer/bin"
speed_khz = 1000
flash = "if-different"
```

[Template](../../../tests/firmware/stands/stlink.example.toml).

`programmer_dir` — абсолютный каталог с `STM32_Programmer_CLI.exe`; на Linux имена без `.exe`.
При SSH оба пути относятся к хосту стенда. Фрагмент target schema 2:

```toml
[stlink]
reset_halt = "monitor reset"
```

## Запуск, сброс и восстановление

Флаги включают SWD `-d`, persistent `-e`, attach `-g`, serial `-i`, частоту, порт,
CubeProgrammer и verify `-s`. `--temp-path`, `-f`, TEMP/TMP изолированы в каталоге запуска.
Готовность — `Waiting for debugger connection`; GDB использует extended-remote.
Сервер может обращаться к SWD ещё до GDB; attach не означает отсутствие воздействия на MCU.

Завершение/recovery — `monitor reset`, `detach`. Persistent принимает нового клиента после
внешнего таймаута. `[stlink].reset_run` не поддерживается. `monitor reset halt` — команда OpenOCD:
ST отвергал её как `Protocol error with Rcmd`. Это привело к разделению диалектов target schema 2
и удалению прежнего `api.toml reset.command`. Команды версии сервера показывает `monitor help`;
они не становятся автоматически частью контракта `Target.reset()`.

## Выявленные ограничения

- Полные F411/F030 серии прерывались USB ERROR, хотя короткие циклы проходили 10/10. F411:
  серверы 7.14.0/7.9.0, GDB из xPack 13/14/15; смена клиента не устранила сбой. Причина неизвестна,
  вопрос 11.2.27 ТЗ открыт. Успех OpenOCD/st-util не является приёмкой этого backend.
- После сбоя иногда и OpenOCD не открывал отладчик до USB-переподключения. Сохраните исходный
  отказ; восстановите BOOT/GPIO после возврата доступа, не повторяйте серию автоматически ради PASS.
- Shared mode `-t` не используется. Lock ST-Link общий с OpenOCD/st-util; сервер принадлежит запуску.
- Наблюдались 950 kHz при запросе 1000 и порт SWV (GDB+1). SWV не используется; аналога `bindto`
  в проверенной справке нет. Учитывайте доступность портов в сети стенда.
- Firmware берётся из журнала; API отладчика не угадывается и может оставаться `null`.

[Приёмка](../API_ACCEPTANCE.md) · [Руководство ST](https://www.st.com/resource/en/user_manual/dm00613038-stm32cubeide-stlink-gdb-server-stmicroelectronics.pdf).
