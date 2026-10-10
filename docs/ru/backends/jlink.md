# J-Link GDB Server

[Backend](index.md) · [English](../../en/backends/jlink.md)

Общие файлы сессии и параметры стенда — [карта TOML](../BACKENDS.md#toml). Фрагмент target дополняет полный профиль MCU.

## Настройка

Backend `jlink` использует SEGGER J-Link GDB Server для Windows/Linux, включая используемые arm64-стенды.
Наличие устройства у SEGGER не означает его приёмку модулем: версии и MCU — в [матрице](../API_ACCEPTANCE.md).

```toml
[probe]
backend = "jlink"
serial = "REPLACE_WITH_JLINK_SERIAL"
executable = "C:/Program Files/SEGGER/JLink/JLinkGDBServerCL.exe"
speed_khz = 1000
flash = "if-different"
```

[Template](../../../tests/firmware/stands/jlink.example.toml).

На Linux имя — `JLinkGDBServerCLExe`. Serial — десятичный USB-номер, не индекс или псевдоним.
`interface` допускает SWD/JTAG; приёмка относится к конкретному подключению. Фрагмент target schema 2:

```toml
jlink_device = "STM32F103CB"

[jlink]
reset_halt = "monitor reset"
```

`jlink_device` находится на верхнем уровне, перед секциями TOML. Без него действует таблица
STM32F103C8T6→STM32F103C8, STM32F103CBT6→STM32F103CB, STM32F030R8T6→STM32F030R8.
Для другого MCU требуется явное имя и отдельная проверка, а не автоматическое усечение строки.

## Жизненный цикл

Runner задаёт `-device`, `-USB`, `-if`, `-speed`, GDB-порт; отключает SWO/Telnet/RTT,
включает localhost-only, nogui, strict и несколько подключений. `-noreset`, `-nohalt`, `-noir`
не заменяют reset сценария. Готовность — `Waiting for GDB connection`.
После extended-remote выполняется `monitor flash breakpoints = 0`: используются аппаратные точки.
Reset/halt — `monitor reset`. Завершение/recovery — `monitor reset`, `monitor go`, `disconnect`.
`[jlink].reset_run` не поддерживается. Журналы: `jlink.log`, `server.log`, `gdb.log`.

## Особенности, повлиявшие на интеграцию

- Для WeAct BluePill-Plus потребовался отдельный mapping CB: имя MCU профиля отличается от имени SEGGER.
- Встроенный J-Link STLink на Nucleo запрашивал окно условий использования и без подтверждения
  не укладывался в готовность. `-nogui` не гарантирует отсутствия такого окна. Первичную настройку
  выполняет владелец; увеличение `startup_timeout_s` (1…120 с) не заменяет ответа на окно.
- Зависание USB-open до MCU не является FAIL прошивки. Сохраните журнал и проверьте доступность J-Link;
  firmware отладчика автоматически не обновляется. [Памятка](../HOWTO.md).
- При SSH проверяется фактический exit сервера, а не только успех helper. Запрошенный SIGTERM
  после EOF допустим; crash/SIGKILL остаются ERROR.

[Документация SEGGER](https://kb.segger.com/J-Link_GDB_Server).
