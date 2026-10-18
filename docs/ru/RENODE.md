# Renode: штатный локальный backend

[Документация](index.md) → [Backend](BACKENDS.md) · [English](../en/RENODE.md)

Добавлено для 0.5.0. Один сценарий — новый процесс Renode и одна машина с одним ядром.
Проверенный маршрут: Renode 1.17, Cortex-M3, Windows и Linux; эмуляторный PASS не HW PASS.
SSH, attach, keep и повторное использование машины пока не поддерживаются.

## Конфигурация

Стенд: [stand.example.toml](../../tests/renode-backend/stand.example.toml).
`schema=1`, таблицы `[emulator]` и `[renode]`; совместное использование `[probe]` запрещено.
`backend="renode"`; `executable` ищется в PATH либо задаётся путём.
`startup_timeout_s=15`, `shutdown_timeout_s=5`: положительные числа до 60 секунд.
`platform` — путь к самодостаточному REPL относительно файла стенда. В первом варианте
includes, filename и сетевые ссылки отклоняются; SVD и Python-модели не подгружаются.
Это ограничение первого адаптера, а не ограничение Renode. Платформа — доверенный код проекта.

Target [schema 3](../../tests/renode-backend/target.toml) требует
`environment="emulator"` и `architecture="cortex-m"`. Поля памяти, `name`, `mcu`,
`breakpoint_limit`, `fault_handlers`, `core_registers`, `diagnostic_registers` сохраняются.
Аппаратные `identity` и `openocd_target` в эмуляторной цели отсутствуют и отклоняются.
Schema 3 с `environment="hardware"` сохраняет обязательные аппаратные поля schema 2.
Schema 1/2 продолжают работать. Stand и target разных окружений несовместимы.
Имена HW_* остаются идентификаторами сценариев; окружение определяется отчётом, не префиксом.

## Запуск и результаты

Из корня репозитория (пути инструментов задаёт пользователь):

```powershell
python tests/renode-backend/run.py --toolchain "$env:STM32_TOOLCHAIN_PATH" --renode renode
```

На Linux та же команда с путём к тулчейну. Скрипт создаёт `session.json` и локальный
`stand.toml` в уникальном каталоге `build/renode-backend/`, выполняет prepare,
PASS, намеренный FAIL, проверку отказа reset, таймаут и повтор PASS.
`summary.json` проверяет ожидаемые исходы; намеренные FAIL/ERROR сохраняются.
Сгенерированный session.json пригоден для обычной команды
`python -m stm32_gdbtest run --session <session.json> --test HW_EMU_STARTUP`.

Runner снимает копию ELF и REPL, запускает Renode, загружает ELF и проверяет GDB/halt,
единственный CPU-thread и файловые LOAD-секции Flash. BSS и произвольная RAM не
выдаются за побайтно проверенные входы. Политики полного программирования Flash запрещены.
Сценарий начинает работу в main; `records.json` включается обычным `[results] capture=true`.
Результаты имеют `mode="emulator"`, `environment="emulator"`, `hardware_accessed=false`;
SHA модели, версия Renode и граница проверки образа сохранены. Их нельзя объединять
с аппаратными свидетельствами DDTT без явного выбора окружения.

При завершении/ошибке/таймауте runner завершает собственные процессы, проверяет закрытие
GDB-порта. Ошибка очистки даёт ERROR; `status_before_cleanup` сохраняет предыдущий исход.
Таймаут сценария — время хоста. Повторное исполнение после ошибки не выполняется.
`reset()` отклоняется с `unsupported_backend`, stage=validation, effect=none: новый
процесс не подменяет семантику сброса внутри сценария. Для чистого состояния запустите
новый сценарий. Произвольная `execute()` остаётся экспертным выходом за эту гарантию.

## Сеть и дальнейшее ускорение

Runner подключается к 127.0.0.1, но штатный GDB-сервер Renode может слушать все интерфейсы.
Loopback-only не гарантируется; это принятое ограничение первой версии. Runner не меняет
firewall. При необходимости изоляцию задаёт окружение (например, контейнер без сети).

Простая перезагрузка ELF не очищает периферию/события. Возможное будущее ускорение:
переиспользовать собственный процесс, пересоздавая машину, с проверкой изоляции прогонов.
Опция keep сейчас отклоняется; сохранение состояния машины потребует отдельного контракта.

[QEMU](QEMU.md) — отдельный минимальный backend.


## Проверка живого окна P3

`python tests/renode-backend/run.py --toolchain <каталог-xPack> --renode <Renode>`
проверяет также async-сценарии [test_live.py](../../tests/renode-backend/test_live.py):
ранний breakpoint, пассивный timeout, два окна, повтор, FAIL/ERROR/SKIP и halt при
завершении. Fault guard моделируется точкой на нейтральной функции, а не физическим
исключением Cortex-M. [Контракт](LIVE_EXECUTION.md).
