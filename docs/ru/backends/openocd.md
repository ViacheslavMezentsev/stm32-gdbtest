# OpenOCD

[Backend](index.md) · [English](../../en/backends/openocd.md)

Общие файлы сессии и параметры стенда — [карта TOML](../BACKENDS.md#toml). Фрагмент target дополняет полный профиль MCU.

## Настройка

Backend `openocd` использует OpenOCD 0.12.0/xPack 0.12.0-7 в проверенных Windows/Linux
конфигурациях. Ubuntu 20.04 OpenOCD 0.10 не содержит используемый `interface/stlink.cfg`;
окружение [Linux-стенда](../LINUX_STAND.md) устанавливает xPack.

```toml
[probe]
backend = "openocd"
serial = "REPLACE_WITH_STLINK_SERIAL"
executable = "openocd"
speed_khz = 1000
flash = "if-different"
```

[Template](../../../tests/firmware/stands/openocd.example.toml).

`interface` выбирает скрипт отладчика; необязательный `transport` выполняется после него.
Не переносите transport из другой сборки без проверки доступных вариантов.
Профиль MCU содержит `openocd_target`, например `target/stm32f4x.cfg`. Фрагмент target schema 2:

```toml
[openocd]
reset_halt = "monitor reset halt"
reset_run = "monitor reset run"
```

Допускается также `monitor reset init` для цели с процедурой инициализации. Без секции действуют
показанные значения. [Полный target F411](../../../tests/firmware/profiles/f411ce/target.toml).

## Запуск и завершение

Runner передаёт interface/target, `adapter serial`, `adapter speed`, отдельный GDB-порт,
`bindto 127.0.0.1`; Tcl/Telnet отключены. Готовность — `Listening on port … for gdb connections`.
GDB использует extended-remote. Reset/halt предшествует проверкам; `load` использует Flash-драйвер
OpenOCD при `if-different`. Завершение — `monitor reset run`, `disconnect`. После таймаута
новый клиент выполняет recovery; переопределение reset/halt не меняет эту последовательность.

## Особенности и исправления

- При миграции schema 1→2 команды перенесены в `[openocd]`. Старые верхнеуровневые поля продолжают
  действовать только для OpenOCD, включая `monitor reset init`.
- Стандартный ST-Link делит lock с `stlink` и `st-util`. Другая семья интерфейса имеет другую
  идентичность lock; это не универсальная блокировка всех адаптеров.
- xPack предупреждает об устаревших `gdb_port`, `tcl_port`, `telnet_port`; синтаксис сохраняет
  совместимость с 0.12.0. Фактическая SWD-частота может быть ниже запроса.
- Через SSH exit `-15` допустим только для штатного SIGTERM helper после EOF. Crash, SIGKILL
  и отсутствие подтверждения остаются ERROR.
- На F429 однажды наблюдались invalid SP и чтение `0x20030020`. В последующих сериях не повторились;
  причина неизвестна. Проверяйте `server.log`/`gdb.log`, а не только `result.warnings`.

OpenOCD восстанавливал BOOT/GPIO после отказов других серверов. Недоступный USB сначала требует
восстановления доступа к самому отладчику. [Матрица и ограничения](../API_ACCEPTANCE.md).
