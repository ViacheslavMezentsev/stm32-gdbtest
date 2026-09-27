# Changelog

Все заметные изменения в этом проекте документируются в этом файле ([English](CHANGELOG.en.md)).
Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).
Версии: [политика](docs/VERSIONING.md).

## [Unreleased]

### Added

- Аппаратная проверка CI-прошивок `Tests/firmware/run_hw.py` (10 шагов: запись, повтор,
  strict identity, полный образ, verify-only, timeout/recovery); на коммите `fbc103d`
  прошли F030R8/J-Link STLink, F103C8/J-Link, F411CE/OpenOCD и F411CE/ST-LINK GDB Server.
- `.clang-format` — стиль исходников C/C++; уровень CI format (`clang-format --dry-run --Werror`).
- `run --prepare-only`: все шаги до GDB-сервера (стенд при наличии, профиль, снимок
  ELF, build manifest, запрошенные контракты, секции и образ, включая полный режим)
  без блокировки отладчика, сервера и подключения; отчёт с `mode: prepare`.
  CMake регистрирует тесты `prepare.<ID>` с метками host и prepare.
- CI GitHub Actions: workflow Docs (ТЗ `check_spec.py --strict`, ссылки, пары RU/EN)
  и Offline (host-тесты на Windows и Linux, сборка CI-прошивок, manifest, `prepare`,
  полный образ и 10 отрицательных ELF-контрактов) без отладчика и платы.
- Docker-образ CI `ci/docker` по закреплённому `ci/dependencies.lock.json`: Ubuntu 24.04,
  xPack GCC 13.3.1/14.2.1/15.2.1 с GDB-Python, CMake 3.28.3, Ninja 1.12.1, CMSIS
  STM32CubeF0/F1/F4; запуск `ci/run_checks.py` локально и в GitHub.
- CI-прошивки `Tests/firmware` на CMSIS без HAL и stm32-cmake-yml: профили F030R8
  (Cortex-M0), F103C8 (Cortex-M3), F411CE (Cortex-M4) со сценариями и контрактами.
- Двуязычные правила сопровождения `docs/ru|en/maintenance.md`, описание проверок
  `docs/ru|en/testing.md`, английская версия журнала изменений.
- J-Link mapping STM32F030R8T6 → STM32F030R8: Nucleo/J-Link STLink/SWD,
  проверены 17 сценариев потребителя, Flash/readback и reset/run; host65.
- Опциональный --image-policy / STM32_GDBTEST_IMAGE_POLICY: полный BIN с явным
  диапазоном/fill, транспортный ELF для GDB, сравнение всех байтов и CRC-32/ISO-HDLC
  по readback на ПК. Verify-only обнаруживает неверный хвост без записи.
- 12 host-регрессий; full-image режим проверен на F411/OpenOCD и F103/J-Link
  с A5/FF хвостом, ожидаемым ERROR, восстановлением и HAL-макросами после load.
- Перенесены и обновлены руководства API, ELF/HAL contracts, HAL-макросов, manifest,
  backend, identity и владения отладчиком; стендовые доказательства связаны ссылками.
- Начальный снимок проверенного прототипа stm32_gdbtest из stm32-hwtest-blackpill.
- Runner/GDB-Python, CMake/CTest, HAL/ELF contracts, JSON/JUnit, три backend,
  межпроектный Windows mutex и независимый пример потребителя.
- Host-тесты с отдельными fixtures и инструкции для человека и ИИ-агента.

### Changed

- Сборка, build manifest, offline-контракты и подготовка образа работают также
  на Linux: разбор команд компилятора по правилам shell, имена binutils по суффиксу
  GDB. Аппаратный запуск по-прежнему только на Windows; отказ на другой ОС выдаётся
  после выбора стенда и профиля, до блокировки отладчика.
- AGENTS.md — краткий перечень правил; ветки `<агент>/<задача>`, слияние без PR,
  подписанные коммиты Conventional Commits; ТЗ ревизии 0.3.
- Промежутки производного BIN заполняются 0xFF. Это не гарантирует заполнение
  дырок при load исходного ELF; политика и отдельный план full-image CRC — docs/IMAGES.md.
- README переработан как пользовательское введение: назначение, подход, состав,
  зависимости и навигация. Срез проверок и ограничений вынесен в docs/STATUS.md;
  добавлена Mermaid-схема.

### Fixed

- BIN формируется только из выбранных загружаемых секций (`objcopy -j`): пустая секция
  с адресом в RAM (например, пустая `.data`) больше не растягивает его до сотен мегабайт
  перед отказом «BIN extent differs». Host-тест и регрессия CI на реальном ELF.
- Скрипты компоновщика CI-прошивок и минимального примера: адрес загрузки `.data`
  выровнен на 4 байта (на Cortex-M0 невыровненное копирование давало HardFault);
  CI отклоняет невыровненные секции загрузки. CI-профиль F103C8 — светодиод PB2
  (WeAct BluePill-Plus).
- docs/STATUS.md: число host-тестов и J-Link mapping F030R8 соответствуют коду.
- Flash сравнивается по загружаемым ELF-секциям/LMA: отличия незагружаемых
  промежутков больше не вызывают ложную ошибку или повторную прошивку.
- Валидация границ/перекрытий до сервера, readback блоками, явная область доказательства.

Релиз/тег ещё не создан; отдельная Git-история и подключение подмодулем уже проверены.
Исторические аппаратные результаты не заменяют проверку нового подключения.
