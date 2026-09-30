# HAL-регрессия NUCLEO-F030R8

[English](README.en.md) · [План и приёмка](../../docs/ru/F030_HAL_REGRESSION.md)

Автономный пример для проверки HAL-макросов, handles/callbacks и force_return
через stm32-gdbtest. Сохраняет 17 сценариев исходного F030-приложения; CMSIS-пример
остаётся отдельно в tests/firmware. Это пока offline-перенос, не новый HW PASS.

Нужны CMake 3.25+, Ninja, Python 3.11+, xPack ARM GCC13 с GDB-Python и
STM32CubeF0 V1.11.6. ARM_TOOLCHAIN_ROOT и STM32CUBE_REPOSITORY задаются через
окружение или CMake cache. CubeMX и stm32-cmake-yml для сборки не нужны.
Из этого каталога:

```sh
cmake --preset debug
cmake --build --preset debug
ctest --preset offline
```

Ожидаются 19 host-тестов: 17 prepare, traceability, fixture inventory/imports/hashes.
Без фильтра CTest запускает аппаратные тесты; не выполнять до выбора стенда.
Build и результаты находятся в build/debug. Личный stand не включён.
Флаги -Og -g3 -fno-lto заданы явно; это отдельный вариант firmware.
Не распространять PASS на Release/LTO/GCC14/15 или другие backend.

Происхождение: [source.json](provenance/source.json) фиксирует исходный коммит,
пути и SHA256 до/после переноса с нормализацией CRLF→LF. Firmware не переработана;
Python-импорты локализованы, добавлены ссылки TECH. Исходный IOC — только provenance,
автоматическая регенерация в этом каталоге не настроена.

Лицензии: [MIT приложения](LICENSE) не переопределяет права ST. В Core/startup/linker
сохранены оригинальные copyright/license notices, включая AS-IS fallback CubeMX.
[Лицензия CMSIS Device](licenses/cmsis-device.txt) и [таблица компонентов Cube](licenses/cube-components.md)
сохранены; HAL/CMSIS библиотеки берутся извне под их собственными лицензиями.
Форматируются только собственные src/app.h и src/*.cpp по src/.clang-format;
Core и сохранённый platform.c исключены из проверки формата.
