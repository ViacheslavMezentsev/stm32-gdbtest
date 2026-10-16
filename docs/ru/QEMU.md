# QEMU: штатный локальный backend

[Документация](index.md) → [Backend](BACKENDS.md) · [English](../en/QEMU.md)

Для 0.5.0: один сценарий — новый процесс QEMU. Первый поддержанный вариант —
`netduinoplus2` (Cortex-M4). Это ограниченная модель платы, а не замена любого STM32
с таким ядром. Эмуляторный PASS не подтверждает работу на реальном MCU.

## Конфигурация

[Пример стенда](../../tests/qemu-backend/stand.example.toml):

```toml
schema = 1
[emulator]
backend = "qemu"
executable = "qemu-system-arm"
startup_timeout_s = 15
shutdown_timeout_s = 5
[qemu]
machine = "netduinoplus2"
semihosting = false
```

`executable` — имя в PATH или путь; таймауты — положительные числа до 60 секунд.
`machine` пока допускает только `netduinoplus2`; неизвестные параметры отклоняются.
Target использует [schema 3](../../tests/qemu-backend/target.toml),
`environment="emulator"`, `architecture="cortex-m"`, без аппаратной identity.
Схемы аппаратных целей 1/2 сохраняются. Правила полей schema 3 — [Renode](RENODE.md).
`probe`, SSH, attach, keep, дополнительные аргументы и другие машины не поддержаны.

Semihosting выключен по умолчанию. `true` включает `enable=on,target=native`:
это исполнение запросов доверенной прошивки к хосту, в том числе файловых операций,
а не изоляция прошивки. Диагностический вывод сохраняется в `server.log`.
Последовательный порт направлен в `uart.log`; наличие файла не доказывает работу UART модели.

## Жизненный цикл и свидетельства

Runner сохраняет ELF, запускает QEMU с `-S`, `-no-reboot`, без GUI/monitor,
с GDB на `127.0.0.1`. TCP-проверка подтверждает только готовность порта; затем GDB
проверяет остановленную цель, единственный CPU-thread и файловые LOAD-секции Flash.
После этого исполнение доходит до main. RAM/BSS не выдаются за проверенные байты ELF.
Полное программирование Flash и аппаратные ожидания identity здесь не применяются.

В результате: `mode="emulator"`, `environment="emulator"`, `hardware_accessed=false`,
версия QEMU, машина и опция semihosting. Модель встроена в исполняемый файл QEMU;
отдельного REPL и его SHA нет. `records.json` включается обычным capture=true.
Таймауты измеряются по времени хоста, не виртуальному времени MCU.
При завершении, FAIL, ERROR или таймауте очищаются собственные процессы и проверяется
закрытие порта. Ошибка очистки даёт ERROR с сохранением предыдущего исхода.
`reset()` отклоняется до команды (`unsupported_backend/validation/none`). Чистое
состояние получается новым сценарием. Произвольная `execute()` — вне этих гарантий.

## Повторяемая проверка

```powershell
python tests/qemu-backend/run.py --toolchain "$env:STM32_TOOLCHAIN_PATH" --qemu qemu-system-arm
```

На Linux — та же команда с Linux-путями. Скрипт собирает нейтральный ELF и создаёт
уникальный `build/qemu-backend/<timestamp>/`: prepare, PASS, намеренный FAIL,
отказ reset, таймаут, повтор PASS, ранний выход сервера и реальный semihosting-вывод.
Сводка `summary.json` проверяет семь ожидаемых исходов; FAIL/ERROR не удаляются.
`session.json` можно использовать с обычным `run --session ... --test HW_EMU_STARTUP`.
`doctor --stand ...` проверяет версию и наличие машины без запуска прошивки/USB.

Проверяемая пара версий: Windows QEMU 11.1.0, Linux QEMU 11.0.0; GCC 14.2.1/GDB-Python.
Версия и модель должны сохраняться при сравнении результатов DDTT.
Методика выбора модели и offline-сборки взята из
[stm32-cmake-yml](https://github.com/ViacheslavMezentsev/stm32-cmake-yml/tree/main/tools/qemu).
Linux-проверки используют существующий образ и новый volume для исходников и сборок;
[локальный CI](local-ci.md). Загрузка ELF не означает полноту эмуляции периферии.
