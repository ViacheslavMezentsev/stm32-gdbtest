# stm32-gdbtest

Проверки STM32 в runtime через GDB-Python. Общая инфраструктура отделена от
прошивки, MCU-профиля и проектных тестов. Основной способ подключения — Git-подмодуль
с закреплённым коммитом. Текущий исходный прототип: 0.1.0.dev0, API_VERSION1;
первый релиз ещё не выпущен. [Версионирование](docs/VERSIONING.md).

## Состав

- stm32_gdbtest/: runner, GDB agent, Target API, contracts, backends и CMake.
- Tests/host и Tests/fixtures: проверки инфраструктуры без платы.
- examples/minimal-consumer: отдельный CMSIS F411 blink и его Python-тест.
- docs/: подключение, написание тестов человеком/агентом и ограничения.

HAL/CMSIS, Cube-пакеты, toolchains, GDB-серверы, SVD и прошивка основного проекта
не входят в поставку. [LICENSE](LICENSE) — MIT; внешние инструменты/библиотеки
поставляются отдельно. Происхождение исходников: [SOURCE](SOURCE.md).

## Требования и проверка без платы

Windows, Python>=3.11, CMake>=3.25, Ninja. Для примера нужны xPack ARM GCC13
с GDB-Python и установленный CubeF4 V1.28.3. Другие MCU/версии требуют проверки.

Из корня модуля:

```powershell
python -B -m stm32_gdbtest --version
python -B -m unittest discover -s Tests/host -v
cd examples/minimal-consumer
cmake --preset debug
cmake --build --preset debug
ctest --preset offline
```

Пути toolchain и Cube задаются ARM_TOOLCHAIN_ROOT/CUBE_F4_ROOT. Пример по умолчанию
ищет их относительно USERPROFILE, локальные настройки не коммитить.

## Подключение к проекту

После отправки начального коммита в репозиторий:

```powershell
git submodule add https://github.com/ViacheslavMezentsev/stm32-gdbtest.git modules/stm32-gdbtest
```

Закрепить проверенный commit/tag в gitlink родительского проекта; не обновлять
зависимость автоматически при configure. В CMake после создания firmware target:

```cmake
include(CTest)
include("${PROJECT_SOURCE_DIR}/modules/stm32-gdbtest/stm32_gdbtest/cmake/STM32GDBTest.cmake")
stm32_gdbtest_attach(firmware_target
    PROFILE_DIR "${PROJECT_SOURCE_DIR}/profiles/myboard"
    MANIFEST_INPUTS "${PROJECT_SOURCE_DIR}/profiles/myboard/firmware_FLASH.ld")
```

Свой профиль содержит target.toml и Tests/{board,requirements.md,contracts.json}.
Тесты создаются в проекте, не внутри подмодуля. Выбор локального стенда:
STM32_GDBTEST_STAND либо CLI --stand. Шаблон OpenOCD: examples/stands/stlink.example.toml;
заменить serial и при необходимости executable, сохранить как *.local.toml в проекте.
CLI из любого cwd можно вызывать абсолютным путём stm32_gdbtest/cli.py.

[Автору тестов](docs/TEST_AUTHORING.md): пошаговый процесс для человека и агента.
[API](docs/API.md): публичные операции и ограничения. [AGENTS](AGENTS.md): правила
изменения ядра. Форматы target/contracts: пример и валидаторы profile.py/contracts.py.

## Что доказано и что ограничено

Прототип проверялся в исходном стендовом проекте на F103/J-Link и F411/ST-Link/OpenOCD,
включая Flash/verify-only, timeout/recovery. F401 также проверялся ранее; аппаратная
совместимость не следует из одного лишь названия семейства. Подробные исторические
доказательства остаются в репозитории происхождения. Consumer F411 имеет собственную
прошивку; его запуск заменяет содержимое Flash, обычный CTest включает HW-тест.

Один firmware target, Windows/Ninja; manifest требует Cube/CMSIS metadata.
-g3 нужен для macros, но не сохраняет неиспользуемые функции. Остановки MCU влияют
на время/IRQ/энергопотребление. Межпроектный mutex действует в одной Windows-сессии
и только для участвующих runner. Vendor tools им не управляются; освобождение
mutex после crash не гарантирует завершения дочернего сервера.

Внешний контроллер стенда (питание, реле, кнопки) запланирован, пока не реализован.
Публикация pip/console executable и поддержка произвольных STM32 не заявляются.
