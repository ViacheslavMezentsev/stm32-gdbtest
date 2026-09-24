# Минимальный потребитель

Самостоятельный CMake/CMSIS F411 blink: свои исходники, startup/linker, профиль,
тест и helper; без stm32-cmake-yml и HAL. BlackPill STM32F411CEU6, LED PC13.
Из этого каталога: cmake --preset debug; cmake --build --preset debug;
ctest --preset offline. Настройки путей — ARM_TOOLCHAIN_ROOT/CUBE_F4_ROOT.
Stand по умолчанию пустой. Обычный CTest включает HW и может записать прошивку;
после опыта восстановить образ, согласованный с владельцем.

[Подключение](../../docs/GETTING_STARTED.md), [автору тестов](../../docs/TEST_AUTHORING.md),
[API](../../docs/API.md). Пример — демонстрация GPIO clock/mode, не универсальное
приложение: core vectors без peripheral IRQ, busy-wait без калиброванного времени.
