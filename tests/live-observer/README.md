# Нейтральный наблюдатель живого окна

[Руководство](../../docs/ru/LIVE_OBSERVER.md) · [English](README.en.md)

Пример API 3: эталон → установка VTOR/SRAM-наблюдателя → `resume(sync=False)` →
`await wait()` / `await halt()` → проверка → снятие → повтор без reset.
Используются штатные runner и Renode backend. Ядро модуля не расширяется.

Из корня репозитория (PowerShell; переменные указывают на ваши установки):

```powershell
python -B tests/live-observer/run.py --toolchain "$env:STM32_TOOLCHAIN_PATH" --gdb "$env:ARM_GDB" --renode "$env:RENODE_BINARY"
python -B tests/host/test_live_observer_example.py
```

Linux: те же аргументы с `$STM32_TOOLCHAIN_PATH`, `$ARM_GDB`, `$RENODE_BINARY`.
Нужны GCC 14.2.1 / GDB с Python и поддержкой API 3, Renode 1.17.0.
Другой компилятор допустим только при успешной проверке пролога и повторной приёмке.
Выход: новый каталог `build/live-observer/<UTC>/`; `--out` задаёт другой новый каталог.
`summary.json` проверяет **8 ожидаемых исходов**: 5 PASS, 2 намеренных ERROR, 1 намеренный
FAIL. `unsupported.json` перечисляет четыре FPB-случая, не поддержанные этой моделью.
Ошибка соединения вместо намеренного исключения не принимается. Исходные result/records
не переписываются. Не запускайте весь набор как обычную кампанию с ожиданием всех PASS.

`prepare.py` только собирает пакет и манифест. `campaign.py` без `--allow-hardware`
только печатает план. Аппаратный маршрут F411 требует отдельного допуска и свежих
проверенных снимков; полная процедура и ограничения — в руководстве.

Файлы: `neutral.c/ld` — нагрузка и владение SRAM; `hook.S` — обёртки;
`test_observer.py` — сценарии; `fpb_adapter.py` — ограниченный F411 remap;
`policy.py` — предусловия; `recovery*.py`, `gdb_recovery.py`, `transport.py` — внешнее
восстановление; `test_*.py`, `fpb_adapter_host.py` — проверки без платы.

Это учебная нагрузка с контролируемыми событиями, не модель реальной платы/RTOS/DMA.
Renode проверяет совместимые инструкции Cortex-M3; аппаратный FPB там не моделируется.
Наблюдение входов функции/ISR не является доказательством всех строк или ветвей.

Раскраска трёх утверждений DDTT: `view/lcov.info`; причины и связи: `view/ddtt-evidence.json`. Подробности привязок — в руководстве.
