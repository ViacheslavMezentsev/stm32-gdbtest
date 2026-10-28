# Renode runner example

[Русский](../../docs/ru/RENODE.md) · [English](../../docs/en/RENODE.md)


```sh
python tests/renode-backend/run.py --toolchain /opt/xpack-arm-none-eabi-gcc-14.2.1-1.1 --renode /opt/renode-1.17.0/renode
```

The same command accepts Windows paths. Uses gdb-py3, a fresh neutral ELF and owned
Renode processes. Results and separate attempts are saved under build/renode-backend.
Intentional FAIL/ERROR/SKIP are checked against expectations; summary.json must contain
only ok=true. The live scenarios use the public runner, not a separate probe launcher.
See [RU](../../docs/ru/LIVE_EXECUTION.md) / [EN](../../docs/en/LIVE_EXECUTION.md).

A1 regressions intentionally exhaust the journal before resume, at a fault guard,
a passive wait, and normal scenario return. They require ERROR with separate audit
diagnostics and VERIFIED execution cleanup. A fault guard is an ordinary neutral
symbol, not a hardware exception. No journal limits are raised to make these pass.

## A2.2: общий result и управление выводом

```sh
python tests/renode-backend/run_report.py --toolchain /opt/xpack-arm-none-eabi-gcc-14.2.1-1.1 --renode /opt/renode-1.17.0/renode
python tests/renode-backend/benchmark_report.py
```

Первый маршрут: 13 ожидаемых исходов full/compact, 1000/10000 проверок, завершённые
reach/write, перехваченный средний FAIL, неожиданный breakpoint, wait/halt, отказ
временного файла и повтор после отказа. Проверка хранения намеренно закрывает
**собственный** временный файл: первичный FAIL сохраняется, ошибка артефакта даёт
command ERROR. `--storage-only` повторяет только этот отрицательный контроль.
Результаты — `build/report-renode`; `summary.json` должен содержать только ok=true.
Runner уже остановил цель в main: следующая штатная точка — observe, а не повторный main.

Benchmark отдельно измеряет накопление обычных Python-значений (tracemalloc),
не транспорт GDB и не полный RSS процесса. Компактное хранение требует CPU/диска;
малые неповторяющиеся журналы могут стать больше. Режим вывода failures не убирает
проверки или их исходы. Используйте общий [читатель](../../docs/ru/API.md#журнал-отчёта-и-вывод-кандидат-060-a22),
не сравнивайте только status и первую/последнюю строку.

## A2.3: три уровня вывода

Добавьте `--summary` к `run_report.py`: 26 запусков сопоставляют full/failures/summary
при full/compact хранении. Сравниваются полные коллекции, вердикты и число проверок;
для summary проверяются SHA-256 источников, повторный расчёт, средний FAIL и частичность
после ошибки хранилища. `summary.json` внутри каталога прогона — производная сводка;
одноимённый файл в корне кампании — список ожидаемых исходов кампании, иной формат.

```sh
python tests/renode-backend/run_report.py --summary --toolchain /opt/xpack-arm-none-eabi-gcc-14.2.1-1.1 --renode /opt/renode-1.17.0/renode
python -m stm32_gdbtest.report_summary build/run/result.json --verify
```

Последний путь замените на result конкретного прогона. Сводка помогает найти событие,
но не заменяет первичные данные и не является входом подтверждения DDTT.

## A3.1: строгая полнота

`run_report.py --summary` проверяет 36 ожидаемых исходов: добавлены потеря records
при работающем ядре с VERIFIED cleanup, перехваченная потеря записи и CheckFailed
без сохранённой строки (compact). Потеря не превращается в PASS, command=2.
Fault injection меняет только лимиты собственного процесса GDB и возвращает их
в finally; это регрессия ядра, а не способ настройки пользовательского сценария.
