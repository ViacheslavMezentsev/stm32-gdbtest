# stm32-gdbtest: API прототипа и миграция

Статус: исходный прототип **0.1.0.dev0**, `API_VERSION = 1`. Это номер описанной
поверхности API, не обещание стабильности релиза 1.0 и не версия GDB. Исходники опубликованы в отдельном Git-репозитории; установка через pip пока не поддерживается. Рабочее имя согласовано;
уникальность имени перед публикацией ещё предстоит проверить.

## Подключение из исходного дерева

```cmake
include("${STM32_GDBTEST_SOURCE_DIR}/stm32_gdbtest/cmake/STM32GDBTest.cmake")
stm32_gdbtest_attach(firmware_target
    PROFILE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/profile"
    MANIFEST_INPUTS "${CMAKE_CURRENT_SOURCE_DIR}/profile/firmware_FLASH.ld")
```

`STM32_GDBTEST_SOURCE_DIR` — корень checkout, содержащий пакет stm32_gdbtest;
в примере consumer это cache PATH. CMake проект обязан включить CTest/enable_testing
и создать firmware target до attach. Поддерживается один target верхнего CMake
каталога, Windows/Ninja, build внутри PROJECT_SOURCE_DIR. PROFILE_DIR и пути
MANIFEST_INPUTS задавать абсолютными. В PROFILE_DIR находятся target.toml и
Tests/board/test_*.py, Tests/requirements.md, Tests/contracts.json (если нужны контракты).
MANIFEST_INPUTS добавляет файлы в snapshot и зависимости relink. SELF_TESTS
дополнительно включает внутренний Tests/host; это опция разработки модуля,
не требование к потребителю. stm32-cmake-yml не является зависимостью API.

Cache `STM32_GDBTEST_GDB` выбирает GDB-Python, `STM32_GDBTEST_STAND` — локальный
TOML стенда. Остальные переменные CMake с этим префиксом внутренние. Генерируемые
session.json/tests.cmake/build-manifest.json не редактировать вручную.
Функция stm32_gdbtest_register — внутренняя, не API интеграции.

## Сценарии Python

```python
from stm32_gdbtest import case

@case("HW_GPIO", timeout_s=20, labels=("gpio",), contracts=("gpio_macros",))
def gpio(t):
    t.reach("loop")
    t.check("GPIOC clock", t.value("__HAL_RCC_GPIOC_IS_CLK_ENABLED()"), 1)
```

Пример требует прошивки с loop и объявленного gpio_macros contract; это не
универсальный тест всех STM32. Декоратор импортируется обычным host Python без
модуля gdb. При collection код теста не выполняется: ID, timeout, labels, contracts
читаются из AST и должны быть литералами. ID соответствует HW_[A-Z0-9_]+,
timeout — целое1..300s, labels — [a-z0-9_-]+, имена contracts — [a-z][a-z0-9_]+.
Декоратор должен называться case без alias. Тест — функция верхнего уровня с одним
параметром Target; исполняется GDB-агентом после boot до main. Project helpers
доступны из корня потребителя. В прошивку тестовые hooks не добавляются.

Публичные операции переданного Target (модуль target импортировать только в GDB):

| Операция | Контракт |
| --- | --- |
| check(name, actual, expected) | Запись результата; несовпадение вызывает CheckFailed → FAIL |
| value(expression) | gdb.parse_and_eval, проверка optimized-out, возвращает int |
| fields(expression, expected) | Поэлементное сравнение скалярных полей с int/C-expression |
| reach(function, when=None) | Одноразовый hardware BP, continue, проверка причины остановки/frame/условия |
| breakpoint(function, temporary=False, when=None) | Hardware BP с проверкой pending и бюджета; возвращает GDB breakpoint |
| set_value(expression, value) | Явная запись с журналом before/after; автор проверяет допустимость MMIO |
| force_return(expression) | Принудительный return из текущего frame с журналом |
| clear() | Удалить принадлежащие Target точки; включая fault traps, если они ещё стоят |

boot/close/on_stop, report/owned/stops и создание Target — lifecycle агента,
не публичный API сценария. Вызовы GDB допустимы только в его основном потоке.
Наличие -g3 сохраняет макросы, но не гарантирует наличие функций/символов;
[HAL_MACRO_GUIDE](HAL_MACRO_GUIDE.md), [HAL_CONTRACTS](CONTRACTS.md).

## CLI и конфигурация

Из корня исходного checkout (из другой папки — через абсолютный путь cli.py):

```powershell
python -B -m stm32_gdbtest --version
python -B -m stm32_gdbtest collect --tests examples/minimal-consumer/profile/Tests/board
python -B -m stm32_gdbtest trace --tests examples/minimal-consumer/profile/Tests/board --requirements examples/minimal-consumer/profile/Tests/requirements.md
python -B -m stm32_gdbtest run --session examples/minimal-consumer/build/debug/hwtest/session.json --test HW_CONSUMER_GPIO --stand path/to/stand.local.toml
```

CLI имеет логическое имя stm32-gdbtest; отдельный console executable будет добавлен
при упаковке. run: --timeout задаёт внешний deadline GDB (0<seconds<=300),
--identity-policy warn|strict. Stand выбирается --stand → STM32_GDBTEST_STAND →
session.stand. Identity: CLI → STM32_GDBTEST_IDENTITY_POLICY → warn.
collect --cmake/--workspace — интерфейс CMake-генерации, обычно вручную не нужен.
Коды run: PASS0 / FAIL1 / ERROR2; ошибка аргументов также2. Ошибки до создания
run-каталога не гарантируют JSON/JUnit. Ожидаемый отказный опыт сохраняет ERROR,
не превращается в PASS самого теста.

Target schema1, контрактная registry schema1, build manifest schema1 и runtime
compatibility schema1 сохраняются. Session — внутренний генерируемый артефакт,
без обещания отдельной стабильной схемы. Источники деталей:
[Подключение](../README.md), [Manifest](MANIFESTS.md),
[TARGET_IDENTITY](TARGET_IDENTITY.md), [GDB_BACKENDS](BACKENDS.md),
[DEBUGGER_OWNERSHIP](DEBUGGER_OWNERSHIP.md). Прямые вызовы runner/contracts/processes
в experiments/host tests — внутренний API разработки; потребителям использовать
CMake/CLI и перечисленные операции Target.

## Переход с hwtest

| Было | Стало |
| --- | --- |
| from hwtest import case | from stm32_gdbtest import case |
| hwtest/cli.py | stm32_gdbtest/cli.py или python -m stm32_gdbtest |
| hwtest/cmake/HwTest.cmake | stm32_gdbtest/cmake/STM32GDBTest.cmake |
| hwtest_attach | stm32_gdbtest_attach |
| HWTEST_SOURCE_DIR / HWTEST_GDB / HWTEST_STAND | STM32_GDBTEST_SOURCE_DIR / STM32_GDBTEST_GDB / STM32_GDBTEST_STAND |
| HWTEST_IDENTITY_POLICY | STM32_GDBTEST_IDENTITY_POLICY |

Старые import/CLI/CMake aliases не предоставляются. Старые environment STAND и
IDENTITY_POLICY вызывают явный отказ runner, чтобы устаревшее указание стенда не
было молча проигнорировано. Внутренние RUN/CONTRACT_REQUEST и smoke env также
переведены на новый префикс; их формирует host, пользователь их не задаёт.

Обновить свои импорты/локальные presets/команды, перенести custom cache значения
на новые имена, убрать старые переменные окружения и заново выполнить configure
и build выбранного preset. Старые CMake cache ключи не используются. Одного запуска
старого CTest без configure недостаточно: он содержит пути прежнего пакета.
Сохранены имена build/test presets, check-hw, host.hwtest, каталоги отчётов hwtest,
ID HW_*, MCU-профили, формат TOML/JSON и namespace mutex (для координации с прошлой
версией, уже поддерживающей межпроектный lock). Миграция не требует добавления тестовых hooks в прошивку.

Git-репозиторий, MIT-лицензия и подключение подмодулем уже подготовлены и проверены.
Остаются release candidate и отдельная Python-упаковка/console entry point; перед PyPI нужна проверка имени. Эта миграция
не означает поддержку произвольного STM32, других ОС или автоматическую остановку
осиротевших серверов после аварии host.
