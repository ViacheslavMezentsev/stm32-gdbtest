# Короткие проверки в Renode

[Документация](index.md) · [English](../en/RENODE_PROBES.md)

`tools/renode_probe.py` — внешний launcher собственной Renode/GDB-сессии, не backend
штатного runner. Нужны Renode 1.17, GDB с Python и ARM GCC. Плата не используется.
Нейтральная модель `tests/renode-startup` содержит Cortex-M3, NVIC, Flash/RAM, без ADC/DMA.

```powershell
python tests/renode-startup/run.py --gdb "$HOME/xpack-arm-none-eabi-gcc-14.2.1-1.1/bin/arm-none-eabi-gdb-py3.exe" --cxx "$HOME/xpack-arm-none-eabi-gcc-14.2.1-1.1/bin/arm-none-eabi-g++.exe" --renode "C:/Program Files/Renode/renode.exe"
```

На Linux те же аргументы с путями Linux. Пример требует закоммиченные входы: сборка нового
ELF, остановка ready, started=1, counter=3, вызов метода существующего объекта и counter=7,
запечатанная кампания и переносимый отчёт. Всё сохраняется в уникальной build/renode-startup.
Для привязки к опубликованным ссылкам push проверенного SHA выполняет владелец.

Для своего ELF:

```text
python tools/renode_probe.py --project PROJECT --elf FILE.elf --model MODEL.repl --scenario SCENARIO.py --map BOUND_MAP.json --runs RUNS --gdb GDB --renode RENODE --case EMU_CASE
```

Модель должна загружаться самостоятельно, без чужого процесса/порта. Сценарий исполняется
в основном потоке Python GDB после подключения к загруженному ELF. Он пишет по пути
`DDTT_PROBE_RESULT` JSON с status PASS/FAIL/ERROR и checks=[{name, passed}], где passed — bool.
Исключение/нет файла/неверные поля/ненулевой GDB код дают ERROR. Результаты — внешний envelope
mode=emulator, purpose=automated, не новое значение поля штатного аппаратного runner.

Предел готовности — до 30 с, GDB по умолчанию 30 с (--timeout до 300), remote response 10 с.
Готовность читается из журнала Renode 1.17, пробный TCP-клиент не занимает GDB-сеанс. Порт
выбирается динамически; гонка bind остаётся возможной и даёт ERROR, не подключение к стенду.
Launcher закрывает только своё дерево процессов и сохраняет исходную ошибку отдельно от
ошибки cleanup. result/run/checks и журналы находятся в папке попытки, публичный отчёт отдельно.

Новый ELF сам по себе не доказывает корректность модели: проверяйте SP/PC, Thumb и пути памяти.
Для ADC/DMA/контроллера Flash нужна настоящая модель либо плата. При вызове метода должен
существовать объект и код функции; inline/LTO могут убрать тело. Закрытие Renode не доказывает
восстановление периферии MCU. Проверяйте отрицательное ожидание и повторный запуск.

Существующий `tests/renode-cache/run.py` — отдельный Windows-пример C++ кэша и ограниченной
Flash-модели с собственным host-контролем; его границы не расширяются автоматически.
Навык [renode](../../skills/stm32-gdbtest-renode/SKILL.md), отчёты [DDTT](PORTABLE_DDTT.md).

Отрицательный контроль: повторите команду с `--negative-control`. Ожидаются FAIL, код 1 и красная точка вызова метода; следующий обычный запуск должен снова дать PASS.

## Проверка пакета P1

На Renode 1.17 проверены Windows и Linux: startup и вызов метода — 3/3. На Windows отрицательный контроль дал 2 подтверждения и 1 отказ (код 1), повторный обычный запуск — 3/3. Отдельно прошёл существующий C++/RAM/кэш-пример. Host-регрессии проверяют отказы готовности и таймаут GDB с очисткой. Это не проверка UART, ADC/DMA или шести физических стендов.

## Регрессия memory/write

Из корня модуля запустите `python tests/renode-startup/run_contracts.py` с теми же
`--gdb`, `--cxx`, `--renode`, что выше. Это настоящий Target API: полный снимок,
RHS-функции со счётчиком (verify on/off, строки таблицы), сужение signed/unsigned,
bool, float, 64-битное значение, enum, указатель, отказ RHS и сохранение PC/SP.
Журналы, checks и хеши входов сохраняются в build/memory-write/<уникальный-id>.
`--module-root` позволяет сравнить другую локальную ревизию модуля тем же сценарием.
На 0.4.1 ожидается исходный ERROR verification_failed из-за второго вызова RHS.
Короткий ответ GDB инъектируется в host-тесте, не воспроизводится этой моделью Renode.

Готовые STM32-платформы, собственные модели и offline-зависимости: [ресурс навыка](../../skills/stm32-gdbtest-renode/references/peripherals.md).
