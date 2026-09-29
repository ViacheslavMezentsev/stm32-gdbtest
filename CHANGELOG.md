# Changelog

Все заметные изменения в этом проекте документируются в этом файле ([English](CHANGELOG.en.md)).
Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).
Версии: [политика](docs/ru/VERSIONING.md).

## [Unreleased]

## [0.1.0-rc.1] — 2026-09-29

Первый кандидат выпуска (версия Python `0.1.0rc1`, `API_VERSION = 1`, ТЗ ревизии 0.21).

### Added

- Локальные пути файла стенда раскрывают `~`, `%VAR%` и `$VAR` (`%USERPROFILE%/.ssh/key`);
  каталог сценариев может называться `tests`.
- `stm32_gdbtest_attach(... PROFILE <target.toml>)`: описание MCU отдельным файлом, общие
  `Tests` (сценарии, требования, контракты) для нескольких вариантов MCU одной прошивки.
- Пакеты подготовленного запуска: `pack` готовит сценарии без оборудования и пишет zip
  с ELF, build manifest, профилем, сценариями и SHA-256 файлов; `run --package` проверяет
  пакет и запускает его на стенде без пересборки; `run_hw.py --package`.
- Workflow Hardware (только вручную): сборка и `pack` на GitHub, запуск пакетов на
  self-hosted раннере со стендом. `run_hw.py --repeat` для прогонов в цикле с `soak.json`.
  Проверено: пакеты с Windows на Orange Pi 5 — три стенда × 10/10; цикл с прерыванием;
  workflow Hardware на раннере-службе Orange Pi 5 — три стенда × 10/10.
  Документация `docs/ru|en/HARDWARE_CI.md`.
- Спецификация метода DDTT 0.2 (Debugger-Driven Testing on Target — тестирование через
  отладчик на целевом устройстве) `docs/ru|en/DDTT.md`: область, термины, принципы,
  модель, требования к сценариям, стендам, инструментам и агентам по RFC 2119;
  stm32-gdbtest — эталонная реализация.
- Удалённый GDB-сервер: таблица `[remote]` стенда. Runner и GDB работают на Windows или
  в WSL, сервер и отладчик — на хосте стенда Linux (Orange Pi 5); одна SSH-сессия с
  пробросом порта и вспомогательным скриптом, блокировка хоста стенда, остановка
  сервера при закрытии или обрыве сессии, только ключи SSH; `doctor` проверяет хост
  стенда. Шаблон `Tests/firmware/stands/remote.example.toml`. Проверено с Windows на
  Orange Pi 5: F411CE/OpenOCD, F103C8/J-Link CE, F030R8/J-Link STLink — по 10/10.
- `doctor` находит GDB в `ARM_TOOLCHAIN_ROOT` и в каталоге xPack по умолчанию на Windows,
  как `run_hw.py`.
- Памятка `docs/ru|en/HOWTO.md`: команды git и псевдоним `git land` (слияние перемоткой
  без PR с удалением ветки), возврат состояния, частые проблемы Linux-стенда,
  отладчиков и Docker; ссылка из AGENTS.md.
- Параметр стенда `startup_timeout_s` (1…120 с, по умолчанию 10) — предел ожидания
  готовности GDB-сервера; сообщение об истечении называет предел и параметр.
- Аппаратный запуск на Linux x86_64 и aarch64 (glibc ≥ 2.31, в том числе Ubuntu 20.04
  на Orange Pi 5): блокировка отладчика `flock` в общем каталоге хоста
  (`STM32_GDBTEST_LOCK_DIR`, по умолчанию `/tmp/stm32-gdbtest-locks`) с обнаружением брошенного владения,
  сервер и GDB в отдельной группе процессов с остановкой `SIGTERM`/`SIGKILL`, имена
  серверов Linux без `.exe`. Проверен на Orange Pi 5: F411CE/OpenOCD, F103C8/J-Link CE, F030R8/J-Link STLink — по 10/10.
- `tools/linux_stand.py`: окружение стенда без root — Python 3.11 (python-build-standalone),
  CMake 3.28.3, Ninja 1.12.1, xPack GCC 13.3.1-1.1, xPack OpenOCD 0.12.0-7 и CMSIS по
  `tools/linux-stand.lock.json` с SHA-256 для x86_64 и aarch64; `env.sh`.
- Команда `doctor`: GDB-Python, binutils, CMake, Ninja, каталог блокировок, стенд,
  `interface/stlink.cfg` OpenOCD и на Linux — ST-Link и J-Link на USB с правами доступа.
- CI: задание `linux-stand` в контейнере `ubuntu:20.04` на x86_64 и aarch64 —
  установка окружения, host-тесты, `doctor`, сборка и подготовка CI-прошивок.
- Документация Linux-стенда `docs/ru|en/LINUX_STAND.md`; ТЗ ревизии 0.7.
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

- README: возможности списком, таблица схем запуска с состоянием проверки, профили MCU
  и проверенные комбинации MCU/отладчик/сервер; STATUS: итоговая проверка кандидата.
- Задание CI `linux-stand` использует контейнер `ubuntu:20.04`, закреплённый по digest.
- Определение проекта: контур проверки прошивки STM32 на оборудовании для агентной и
  ручной разработки, по устройству — фреймворк тестирования через отладчик. README,
  карты документации, схемы размещения стенда в STATUS, выбор схемы в начале работы,
  контур агента в написании тестов; ТЗ ревизии 0.10.
- `run_hw.py` работает на Linux (toolchain и Cube из `env.sh`) и записывает ОС и
  архитектуру хоста в `summary.json`.
- Документация перенесена в `docs/ru/` и получила английские версии в `docs/en/`,
  карты документации `index.md` и строки навигации; добавлен README.en.md. Страницы
  сверены с текущим функционалом: подготовка без оборудования, Linux для offline-части,
  полный образ через ST-LINK GDB Server, контекст макросов в единице компиляции,
  адрес размера Flash F030, проверенные стенды; ТЗ ревизий 0.5 и 0.6.
- Сборка, build manifest, offline-контракты и подготовка образа работают также
  на Linux: разбор команд компилятора по правилам shell, имена binutils по суффиксу
  GDB (аппаратный запуск на Linux — в разделе Added).
- AGENTS.md — краткий перечень правил; ветки `<агент>/<задача>`, слияние без PR,
  подписанные коммиты Conventional Commits; ТЗ ревизии 0.3.
- Промежутки производного BIN заполняются 0xFF. Это не гарантирует заполнение
  дырок при load исходного ELF; политика и отдельный план full-image CRC — docs/IMAGES.md.
- README переработан как пользовательское введение: назначение, подход, состав,
  зависимости и навигация. Срез проверок и ограничений вынесен в docs/STATUS.md;
  добавлена Mermaid-схема.

### Fixed

- `reach` сравнивает имя кадра без суффиксов `[clone …]`, `const` и параметров: с LTO GDB
  называет кадр по символу ELF (`HmiManager::init() [clone .constprop.0]`), и верная
  остановка давала FAIL.
- Build manifest с пустыми `cube_packages` и `library_versions` больше не отклоняется:
  HAL и CMSIS могут быть не из пакета `STM32Cube_FW_*` (Arduino Core STM32).
- Удалённый сервер: runner шлёт в SSH-сессию сигнал присутствия каждые 2 с; при обрыве
  связи без закрытия соединения (Wi-Fi, кабель, сон) сервер на хосте стенда
  останавливается и отладчик освобождается через 15 с, а не через часы. Проверено на
  Orange Pi 5 выдёргиванием кабеля.
- `tools/linux_stand.py` повторяет загрузки и `git fetch` при временных ошибках сервера
  (до 4 попыток с паузами); задания CI кэшируют закреплённые загрузки.
- `tools/linux_stand.py install --only …` проверяет только выбранные компоненты: задание
  `prepare` аппаратного CI больше не падает на отсутствующем OpenOCD.
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

Итоговая проверка пройдена на коммите `2143665` (CI, аппаратные прогоны на стендах, сценарии
потребителя) — [перед релизом](docs/ru/VERSIONING.md#перед-релизом). Тег `v0.1.0-rc.1` ставится на
коммит с уточнённой документацией: код в нём совпадает с проверенным.
