# Начало работы

[Документация](index.md) → Начало работы · [English](../en/GETTING_STARTED.md)

Основной способ подключения stm32-gdbtest — Git-подмодуль с закреплённым коммитом.
Python-сценарии и настройки платы находятся в проекте потребителя. Команды проверки
модуля ниже выполняются из его отдельного checkout и создают build-артефакты; в
подключённой зависимости проекта их лучше запускать в отдельной рабочей копии.

## Требования

- Аппаратный запуск: Windows или Linux (x86_64, aarch64, glibc ≥ 2.31), Python ≥ 3.11,
  CMake ≥ 3.25, Ninja, ARM GCC с `arm-none-eabi-gdb-py3` (GDB со встроенным
  Python ≥ 3.11), SWD-отладчик и его GDB-сервер (OpenOCD, ST-LINK GDB Server или
  J-Link GDB Server).
- На Linux всё, кроме ПО J-Link и правил udev, ставится без root сценарием
  `tools/linux_stand.py`, в том числе на Ubuntu 20.04 ([Linux-стенд](LINUX_STAND.md)).
- Сборка, build manifest и подготовка без оборудования (`run --prepare-only`) —
  также в Docker-образе CI ([проверки и CI](testing.md)).
- `python -B -m stm32_gdbtest doctor [--stand <стенд>]` проверяет окружение без
  обращения к отладчику.
- Проверенные версии и платы — [текущее состояние](STATUS.md). Другие MCU и
  версии требуют собственной проверки.

## Проверка модуля без платы

Из корня модуля:

```powershell
python -B -m stm32_gdbtest --version
python -B -m unittest discover -s Tests/host -v
cd examples/minimal-consumer
cmake --preset debug
cmake --build --preset debug
ctest --preset offline
```

Пример `examples/minimal-consumer` рассчитан на Windows: xPack ARM GCC 13 с
GDB-Python и установленный STM32CubeF4 V1.28.3. Пути задаются `ARM_TOOLCHAIN_ROOT`
и `CUBE_F4_ROOT`, по умолчанию ищутся относительно `USERPROFILE`; локальные настройки
не коммитятся. `ctest --preset offline` выполняет traceability, подготовку
`prepare.HW_CONSUMER_GPIO` и offline-проверку контрактов без подключения к плате.

Полный набор проверок CI (Windows и Linux, три GCC, три MCU) запускается одной
командой в Docker-образе — [проверки и CI](testing.md).

## Подключение к проекту

В проекте потребителя:

```powershell
git submodule add https://github.com/ViacheslavMezentsev/stm32-gdbtest.git modules/stm32-gdbtest
```

Закрепите проверенный коммит или тег в gitlink родительского проекта; зависимость
не обновляется автоматически при configure. В CMake после создания firmware target:

```cmake
include(CTest)
include("${PROJECT_SOURCE_DIR}/modules/stm32-gdbtest/stm32_gdbtest/cmake/STM32GDBTest.cmake")
stm32_gdbtest_attach(firmware_target
    PROFILE_DIR "${PROJECT_SOURCE_DIR}/profiles/myboard"
    MANIFEST_INPUTS "${PROJECT_SOURCE_DIR}/profiles/myboard/firmware_FLASH.ld")
```

Профиль содержит `target.toml` и `Tests/` (`board/test_*.py`, `requirements.md`,
`contracts.json`). Тесты создаются в проекте, не внутри подмодуля. Локальный стенд
выбирается `STM32_GDBTEST_STAND` или `--stand`; шаблоны —
`examples/stands/stlink.example.toml` и `Tests/firmware/stands/*.example.toml`.
Замените серийный номер и при необходимости путь к серверу и сохраните файл как
`*.local.toml` в проекте. CLI из любого каталога вызывается по абсолютному пути
`stm32_gdbtest/cli.py`.

Перед первым аппаратным запуском полезно выполнить
`run --prepare-only --stand <стенд>`: он проверит стенд, профиль, manifest,
контракты и образ без обращения к отладчику.

## Дальше

- [Написание тестов](TEST_AUTHORING.md) — процесс для человека и ИИ-агента.
- [API и CLI](API.md) — публичные операции и ограничения.
- [Сопровождение](maintenance.md) и [AGENTS.md](../../AGENTS.md) — правила изменения ядра.
- Форматы профиля и контрактов — примеры и валидаторы `profile.py`, `contracts.py`.
