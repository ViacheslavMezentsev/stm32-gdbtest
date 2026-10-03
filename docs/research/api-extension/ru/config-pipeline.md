# M4: сквозной prepare → пакет → GDB-сценарий

[Исследование](index.md) · [English](../en/config-pipeline.md)

03.10.2026, продолжение [транспорта M4](config-transport.md), база 2448284.
[Pipeline](../../../../tests/api-extension/session_pipeline.py),
[повторяемый запуск](../../../../tests/api-extension/run_config_pipeline.py),
[host-тесты](../../../../tests/api-extension/test_session_pipeline.py).
Ядро и прошивки не изменены; подключений к MCU нет.

## Реальный локальный опыт

1. На существующем ELF F030 захвачены session/target/api/image. API задаёт
   max_records=7 и неизвестную секцию measurement с samples=3 и TOML-датой.
2. Pipeline копирует ELF, manifest, сценарии и захваченный target в временный
   проект; проверяет manifest относительно ELF и точных байтов target.
3. Штатный runner выполняет HW_CI_ADC_UNITS с prepare_only=True и захваченной
   full-image policy. PASS: ELF-контракт, образ и его carrier проверены без MCU.
   Журналы копируются из временного проекта до его удаления.
4. Штатный pack создаёт schema-1 ddtt-package с ELF, manifest, сценариями и
   дополнительным research/config.json через существующий include-механизм.
   Исходный каталог TOML перемещается: прежние ссылки становятся недоступны.
5. Штатный open_package проверяет хеши и восстанавливает пакет. Исследовательский
   open_configured восстанавливает снимок, сверяет его target с профилем пакета
   и снова проверяет manifest. cwd GDB находится в каталоге получателя.
6. Настоящий GDB-Python создаёт настоящий Target без boot/connect. Оболочка
   ConfiguredTarget предоставляет read-only свойства и делегирует check.
   Все шесть проверок PASS: MCU из профиля, пользовательское значение, тип date,
   отсутствие defaults в props.data, наличие defaults в config и работа Journal
   с лимитами из config. Обработчик stop закрывается через Target.close.

Это проверка инфраструктуры на настоящем ELF/GDB, а не выполнения firmware.
Команд target remote/continue нет; connection_attempted=false. Сценарий GDB —
отдельный исследовательский smoke-script, не запуск board case через production agent.
Journal подключён явно; методы record/records не добавлены в Target.

## Host-регрессия

Четыре новых теста проверяют полный pack/open/facade путь с синтетическим ELF,
недоступными исходными конфигурациями, неизменяемостью и делегированием; отказ
при устаревшем profile hash до preflight; отказ упаковки после ERROR preflight;
отказ при расхождении capsule target и packaged profile даже после обновления
хеша файла в manifest пакета. Host-double PASS не выдаётся за проверку ELF.
Дополнительно сохранились прежние 64 теста M2–M4/E1–E4.

Исходный ELF реального опыта: SHA256
`d6bfed5a23f6d25935df02e4b5b0b4049c950c61313132cc99e1106c400f4206`.
Среда: Windows, xPack GDB 14.2.90.20240526-git, Python внутри GDB; backend не
запускается. Raw-пакет/ELF/логи остаются gitignored; [результат](../results/config-pipeline.json)
не содержит персональных путей. Отрицательные host-исходы ожидаемы и проверяются тестами.

## Границы результата и следующий шаг

Основной исследовательский сквозной путь M4 подтверждён. Это ещё не готовая
производственная миграция: --package самостоятельно не подключает config_props,
production agent/CTest не используют оболочку, SESSION_CONFIG доступен только
в research-обвязке. На Orange Pi/по SSH опыт не запускался. Старые пути ядра
проверялись в предыдущем отчёте; эти результаты не объявляются новыми прогонами.

До M5 требуется согласовать: base64 исходных TOML как транспорт, поведение при
разных defaults/версиях, форму config_props для старого режима и судьбу конфликтов
пользовательских имён с будущими API-параметрами. Ресурсные верхние границы Q6/Q19
также открыты. Далее — сводка принятых решений и оставшихся вопросов перед
нормативной ревизией ТЗ. Перенос в ядро по-прежнему требует разрешения владельца.

Итог host-проверок: Linux CI 68/68 PASS; Windows 67 PASS/1 skip (CMake без
компилятора в PATH). Реальный prepare и GDB-smoke выше выполнялись на Windows.
