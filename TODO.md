# Дорожная карта

## Текущая работа

- Текущая ветка `codex/f030-hal-regression-plan` от `cea01f9`: подготовлен
  [план HAL fixture](docs/ru/F030_HAL_REGRESSION.md), исходная база потребителя
  `0c8c966`, полный начальный набор 17 сценариев. Только документация;
  новые HW-проверки не выполнялись. Windows/Linux docs 3/3 PASS.
  Далее зависимые ветки fixture → CI →
  HW validation, публикация пакетом по готовности. HAL-профиль не удалять.
- Завершён пакет ADC_BUSY → RTC_DEADLINE → CMSIS acceptance → lowercase:
  все четыре SHA прошли Docs и Offline, включены в main `cea01f9`.
  Потребитель обновил gitlink/каталоги tests: `0c8c966`, пять профилей CI PASS,
  ветка включена в main. Итоговые имена: tests и remote.toml; API_VERSION=1.
  Прежние16 +2 новых HW-сценария выполнены на одном ELF, HAL восстановлен.

- `codex/f030-cmsis-rtc` от `f494ab1`: RTC Alarm A/LSI и два сценария;
  16/16 HW PASS на новом ELF, HAL восстановлен. [Протокол](docs/ru/F030_CMSIS_RTC.md).
  Далее отказные ветви и итоговая приёмка HAL→CMSIS для F030.
  API ядра без изменений; ТЗ 0.33. F030 CTest 17/17, Windows host 96
  (8 skips), Linux docs/host/9 firmware pairs 13/13 PASS; strict ТЗ и формат PASS.

- `codex/f030-cmsis-sleep` от `a84b742`: два новых Sleep/WFI сценария,
  2/2 HW PASS; прежние 12 не повторялись, ELF тот же. HAL восстановлен.
  Проверки: F030 CTest 15/15, Windows host 96 (8 skips), Linux docs/host/
  9 пар firmware 13/13 PASS; strict ТЗ PASS.
  [Протокол](docs/ru/F030_CMSIS_SLEEP.md). Далее RTC и оставшиеся отказы.


- `codex/f030-cmsis-adc-units` от `a6c0426`: преобразование F030 ADC и
  7 численных/14 невалидных наборов; 12/12 HW PASS, HAL восстановлен.
  Проверки: F030 CTest 13/13, Windows host 96 (8 skips), Linux docs/host/
  9 пар firmware 13/13 PASS; strict ТЗ и формат PASS.
  [Протокол](docs/ru/F030_CMSIS_ADC_UNITS.md). Далее RTC/Sleep и отказы.


- `codex/f030-cmsis-adc-dma` от `5883316`: ADC/DMA raw и timeout F030,
  9/9 HW PASS, HAL восстановлен. [Протокол](docs/ru/F030_CMSIS_ADC_DMA.md).
  Проверки: host Windows 96 (8 skips), F030 CTest 10/10; Linux три профиля
  × GCC13/14/15 подтверждены первоначальным и исправленным F030-прогонами.
  Далее преобразование в физические единицы и численные векторы, RTC/Sleep.


- `codex/f030-cmsis-timer` от `40fafac`: TIM3/IRQ добавлены в F030 fixture;
  6/6 HW PASS на Nucleo/ST-Link/OpenOCD; HAL восстановлен.
  Offline: Windows host 96 (8 skips), Linux docs/host/9 firmware pairs 13/13 PASS,
  F030 CTest 7/7; strict ТЗ и формат PASS.
  [Протокол](docs/ru/F030_CMSIS_TIMER.md). Далее ADC/DMA/арифметика, RTC, Sleep.


- `codex/f030-cmsis-baseline` от `4601888`: первый этап CMSIS F030,
  boot/clock/GPIO/blink — 4/4 HW PASS (ST-Link/OpenOCD), HAL восстановлен.
  Windows host: 96 тестов, 8 skips; Linux docs/host/firmware: 13/13 PASS,
  F030/F103/F411 × GCC13/14/15; strict ТЗ: 0 ошибок/предупреждений.
  [Протокол](docs/ru/F030_CMSIS_BASELINE.md). Следующий этап — таймер/IRQ,
  далее ADC/DMA/RTC. Оптимизация CI остаётся после переноса примеров.


- `codex/cmsis-migration-inventory` от `bc07625` — [миграция примеров](docs/ru/CMSIS_MIGRATION.md)
  ([English](docs/en/CMSIS_MIGRATION.md)): сопоставлены 17 HAL-сценариев F030
  с двумя CMSIS-сценариями. Build/offline 3/3 PASS, без HW. Далее F030
  boot/clock/GPIO/blink, затем периферия и другие профили. Оптимизация CI — после переноса.
  Также переименован корневой Tests → tests; вложенные каталоги потребителей
  сохраняют совместимость. Gitlink потребителя менять после публикации и CI модуля.
  Проверки: Windows host 96 (8 skips); архив Git index извлечён в Linux filesystem,
  docs/host/firmware GCC13 для F030/F103/F411 — 7/7 PASS. ТЗ strict: 0 ошибок,
  0 предупреждений. Новый HW-прогон не выполнялся.

- `claude/tech-spec-0.1` — ТЗ ревизии 0.1 и правила коммитов; слита в main (PR #2).
- `claude/maintenance-rules` — AGENTS.md в виде краткого перечня, docs/ru|en/maintenance.md,
  ТЗ ревизии 0.2; слита в main.
- `claude/offline-ci` — подготовка к 0.1.0: `run --prepare-only`, offline-часть на Linux,
  CI-прошивки F030R8/F103C8/F411CE, Docker-образ, workflows Docs и Offline, ТЗ 0.3;
  проверено локально в Docker-образе (13/13: docs, host, 9 пар firmware); слита в main.
- `claude/hw-validation` — аппаратная проверка CI-прошивок до v0.1.0 (`tests/firmware/run_hw.py`:
  F411CE/ST-Link, F103C8/J-Link, F030R8/J-Link STLink), `.clang-format` и уровень format в CI,
  LED BluePill-Plus на PB2, выравнивание `.data`; 4 стенда × 10/10 шагов на `fbc103d`,
  ТЗ 0.4, STATUS; слита в main.
- `claude/bin-load-sections` — BIN только из выбранных секций (вопрос 11.2.17), ТЗ 0.5.
- `claude/docs-ru-en` (от `claude/bin-load-sections`) — сверка документации с кодом,
  перенос в `docs/ru` с переводами в `docs/en`, README.en.md, ТЗ 0.6. Далее: выпуск
  v0.1.0-rc.1 с повторной аппаратной проверкой на итоговом коммите.
- `claude/linux-stand` — все сценарии размещения стенда до v0.1.0, группы A и B:
  аппаратный запуск на Linux (`flock`, группы процессов), окружение Ubuntu 20.04 без
  root `tools/linux_stand.py`, `doctor`, CI `linux-stand`, ТЗ 0.7; слита в main.
- `claude/remote-server` — группа C (удалённый GDB-сервер по SSH, ТЗ 0.9), `doctor` ищет
  GDB как `run_hw.py`, определение проекта как реализации DDTT, спецификация DDTT 0.1,
  сверка документации с кодом (ТЗ 0.10).

## Сценарии размещения стенда до v0.1.0

- [x] Windows локально (проверено на 4 стендах).
- [x] Orange Pi 5 (Ubuntu 20.04 aarch64) локально — 3 стенда × 10/10.
- [x] WSL2 (Ubuntu 20.04 x86_64) → сервер на Orange Pi 5 по SSH — 3 стенда × 10/10 (ТЗ 0.15, TC-112).
- [ ] Технический долг: WSL2 + usbipd-win (у владельца конфликт с фильтрами USB USBPcap
  и nxusbf) и отдельный Linux-ПК x86_64 с отладчиком — реализовано, на оборудовании не проверялось.
- [x] Группа C: runner и GDB на Windows или в WSL, GDB-сервер и отладчик на Orange Pi 5
  по SSH (туннель, удалённая блокировка, таблица `[remote]`, только ключи) — реализовано
  (`claude/remote-server`, ТЗ 0.9), проверено с Windows: 3 стенда × 10/10; обрыв связи
  (сигнал присутствия, ТЗ 0.13) проверен выдёргиванием кабеля Orange Pi.
- [x] Группа D: сборка в одном месте, запуск на Orange Pi 5 (`pack`, `run --package`);
  аппаратный CI на self-hosted runner aarch64 (workflow Hardware, вопрос 11.2.16 ТЗ);
  прогоны в цикле (`run_hw.py --repeat`) — реализовано (`claude/prepared-runs`, ТЗ 0.12);
  проверено на Orange Pi 5: пакеты и цикл; workflow Hardware на раннере-службе — 3 стенда × 10/10.

## Этапы

- [x] Выделить ядро, API прототипа, самостоятельный пример и host fixtures.
- [x] Создать отдельную Git-историю и проверить подключение закреплённым подмодулем.
- [x] CI до GDB-сервера: host-тесты Windows/Linux, CI-прошивки на GCC 13/14/15, `prepare`.
- [x] Проверить новое подключение: проект потребителя на STM32G474 (Arduino Core STM32,
  stm32-cmake-yml, Windows → Orange Pi 5) — сценарий загрузки PASS; найден и исправлен отказ
  manifest без пакетов STM32Cube.
- [ ] Выпустить v0.1.0-rc.1: версия `0.1.0rc1`, CHANGELOG, ТЗ 0.21 (`2143665`); итоговая проверка
  пройдена (CI, 4 + 3 стенда, workflow Hardware, G474 потребителя 4/4); README уточнён — остался тег владельцем.
- [ ] Затем v0.1.0.
- [x] Перенести страницы `docs/*.md` в `docs/ru/` и добавить английские версии, README.en.md.
- [ ] Описывать совместимость по MCU/HAL/GDB/backend, а не по количеству тестов.
- [ ] Надзор за дочерними процессами при аварии host (Job Object и др.).
- [ ] Независимость от системы сборки (вопрос 11.2.23 ТЗ): стабильная схема `session.json` и команда
  её создания с явными параметрами; необязательный build manifest; к рассмотрению до v0.1.0.
  Позже — manifest из `compile_commands.json` без Ninja.
- [ ] Упаковка Python и console entry point как дополнительный способ поставки.
- [ ] Устранить обязательные OpenOCD-поля target schema и расширить переносимость build manifest.
- [ ] Документировать расширение профилей; не обещать поддержку непроверенного MCU.

## Внешнее согласованное управление стендом — отложено

- [ ] Контроллер в обычном host Python: источники питания, реле, имитаторы кнопок,
  измерительные приборы; драйверы оборудования остаются в проекте стенда.
- [ ] Команды/подтверждения и синхронизация с GDB-агентом, таймауты и журнал действий.
- [ ] Владение внешними ресурсами, безопасное завершение после ошибки/отмены.
- [ ] Сценарий power-cycle: ожидаемая потеря SWD/RSP, reconnect, повторная identity/Flash проверка.
- [ ] Разделять наблюдение работающего MCU и действия при halt; GDB API только в
  основном потоке GDB, без вызовов из фоновых потоков.

Этот интерфейс пока не реализуется; он учитывается как будущая граница ядра.

- [x] Перенести в модуль каноническую документацию API/contracts/macros/manifest/backend/identity/locks.
- [ ] При каждом изменении механизма обновлять его документацию здесь; результаты стендовых проверок — в проекте потребителя.

- [x] Оформить README как пользовательское введение и вынести подробное текущее состояние в docs/ru/STATUS.md.

## Образы и переносимость

- [x] Проверять Flash по ELF load sections/LMA, пропуская незагружаемые промежутки.
- [x] Явный BIN gap-fill 0xFF, границы/перекрытия до сервера, отрицательные host-тесты.
- [x] Полный образ с явным диапазоном/fill: BIN → односекционный ELF, readback
  gaps/tail, CRC-32/ISO-HDLC на ПК, единый payload debug/programming; без CRC-поля.
- [ ] CRC-поле/исключения и другие алгоритмы, сверка с MCU CRC, отдельный offline
  export/prepare CLI (полный режим через ST GDB Server уже проверен).
- [ ] Разделить адаптеры toolchain, MCU memory/identity и архитектурную диагностику;
  текущая доработка не объявляет production-поддержку RISC-V.

- [x] Проверить профиль Cortex-M0 через J-Link STLink: F030R8, существующие API/schema, host65 и 17 HW-сценариев потребителя.
