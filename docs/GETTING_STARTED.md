# Начало работы

Основной способ подключения stm32-gdbtest — Git-подмодуль с закреплённым коммитом.
Python-сценарии и настройки платы находятся в проекте потребителя. Команды проверки
модуля ниже выполняются из его отдельного checkout; они создают build-артефакты.
В подключённой зависимости проекта такие проверки лучше запускать в рабочей копии.

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

В проекте потребителя:

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

[Автору тестов](TEST_AUTHORING.md): пошаговый процесс для человека и агента.
[API](API.md): публичные операции и ограничения. [AGENTS](../AGENTS.md): правила
изменения ядра. Форматы target/contracts: пример и валидаторы profile.py/contracts.py.


Текущий объём проверки и ограничения — [STATUS](STATUS.md).
