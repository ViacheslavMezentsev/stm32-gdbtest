# C++-контекст: воспроизводимый пример

[English](README.en.md) · [TECH-019](../../docs/ru/TESTING_TECHNIQUES.md#tech-019)

Отдельная вычислительная прошивка: Converter::apply(int/float), this, преобразование GDB Value,
поля объекта и выход из области видимости. Не инициализирует периферию. Нет RTTI/exceptions/LTO,
везде soft-float. Нужны CMake ≥3.25, Ninja, Python ≥3.11 и GNU Arm GCC/G++ с GDB-Python.

Из корня репозитория (пути инструментов/стенда замените своими):

```sh
cmake -S tests/cpp-context -B tests/cpp-context/build/f030-og -G Ninja -DCMAKE_TOOLCHAIN_FILE=../firmware/cmake/arm-gcc.cmake -DARM_TOOLCHAIN_ROOT=/path/to/toolchain -DCI_PROFILE=f030r8 -DOPT=Og -DSTM32_GDBTEST_GDB=/path/to/arm-none-eabi-gdb-py3
cmake --build tests/cpp-context/build/f030-og
python -m stm32_gdbtest run --session tests/cpp-context/build/f030-og/hwtest/session.json --test HW_CPP_CONTEXT --prepare-only
python -m stm32_gdbtest run --session tests/cpp-context/build/f030-og/hwtest/session.json --test HW_CPP_CONTEXT --stand /path/to/stand.local.toml
```

Последняя команда подключается к MCU и может заменить прошивку. Перед запуском сохраните исходный
ELF/session и оговорите восстановление. После опыта запустите BOOT/GPIO исходной CI-сессии с тем же
стендом (HW_CI_BOOT, HW_CI_GPIO). reset_run сам по себе не возвращает прежний образ Flash.

CI_PROFILE: f030r8, f103c8, f401cc, f411ce, f429zi, at32f403a; OPT: Og или O2. Для каждого варианта
используйте отдельный каталог build внутри tests/cpp-context. Профили и linker scripts берутся из
соседнего tests/firmware. STM32Cube/Artery SDK для этой вычислительной прошивки не требуется.

Образец сценария — [test_cpp_context.py](profile/tests/board/test_cpp_context.py). Для сохранения records
подключите [захват](../../docs/ru/RESULTS.md) в отдельном session.toml. Недоступный input вне метода
отличается от optimized_out: второй случай может не возникнуть даже при O2. Сценарий проверяет
reach без кавычек (int) и с одинарными кавычками GDB (float; исправлено в Unreleased). C++-объекты живут в GDB только в текущем контексте;
в журнал уходят простые снимки. [Объём проверки](../../docs/ru/API_ACCEPTANCE.md).
