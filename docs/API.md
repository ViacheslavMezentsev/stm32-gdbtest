# API исходного прототипа

Версия0.1.0.dev0, API_VERSION1. Source-checkout API, ещё не стабильный1.0.

- `from stm32_gdbtest import case`: host-safe импорт без gdb.
- `@case("HW_ID", timeout_s=20, labels=("gpio",), contracts=("gpio_macros",))`:
  литералы верхнеуровневой функции, один параметр Target. Timeout1..300s.
- Target: check(name,actual,expected), value(expression), fields(expression,expected),
  reach(function,when=None), breakpoint(function,temporary=False,when=None),
  set_value(expression,value), force_return(expression), clear(). clear удаляет
  также fault traps; boot/close/on_stop — внутренний lifecycle агента.
- CLI: python -B -m stm32_gdbtest --version/--help; collect --tests PATH;
  trace --tests PATH --requirements FILE; run --session FILE --test HW_ID
  [--stand FILE] [--timeout SECONDS] [--identity-policy warn|strict].
- Stand: CLI → STM32_GDBTEST_STAND → session.stand. Identity: CLI →
  STM32_GDBTEST_IDENTITY_POLICY → warn. Старые HWTEST_STAND/IDENTITY_POLICY дают ERROR.
- Коды run: PASS0/FAIL1/ERROR2. Ошибка до run-каталога может не иметь JSON/JUnit.
- CMake: stm32_gdbtest_attach(target PROFILE_DIR ABSOLUTE_PATH
  [MANIFEST_INPUTS ABSOLUTE_FILES...] [SELF_TESTS]). Один firmware target Windows/Ninja,
  build внутри PROJECT_SOURCE_DIR. CMake cache: STM32_GDBTEST_GDB, STM32_GDBTEST_STAND.
  Генерируемая session и функции регистрации — внутренний интерфейс.

Target schema1, registry contracts schema1, build manifest schema1 и runtime
compatibility schema1 независимы. Target.toml пример — examples/minimal-consumer/profile;
точная проверка полей — profile.py. Flash size address нужен runtime guard.
Contracts проверяются отдельным offline GDB до сервера: функции/types/fields/enums,
source_reviews hashes и macros{context,expressions}. NULL contracts требуют реально
проверенного HAL-source hash в manifest. Fixtures не подставлять в HW проверки.

Runner/agent/internal JSON plumbing и прямые импорты остальных модулей — внутренний
API. Пользовательский тест получает Target, а не конструирует его. Test helper
импортируется из корня проекта. GDB-Python не наследует автоматически библиотеки
host Python; не переносить вызовы GDB API в фоновые потоки.

Занятый mutex, отсутствующий символ, несовпадение manifest и невалидный контракт
должны завершать запуск ошибкой, не пропускать проверку. DEV_ID mismatch по умолчанию
WARNING с продолжением по выбранному профилю, strict запрещает; размер Flash
проверяется до записи. Это не разрешение использовать произвольный профиль MCU.
