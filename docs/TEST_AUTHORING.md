# Написание тестов человеком и ИИ-агентом

Одинаковый процесс применяется к ручной работе и генерации агентом. Для человека
достаточно редактора Python/VS Code и команд ниже; агент не является зависимостью.

1. Сформулировать наблюдаемое требование и его ID в Tests/requirements.md.
   Определить допустимое влияние halt/reset и критерий ошибки.
2. Подготовить target.toml по конкретному MCU/плате и firmware: Flash/identity,
   breakpoint budget, fault handlers. Собрать Debug с -g3, проверить ELF/manifest.
3. Написать верхнеуровневую функцию test_*.py в profile/Tests/board. Не изменять
   модуль для добавления проектного сценария; helpers хранить в проекте.
4. Если используются HAL/macros, выбрать чистые getter/predicate выражения и
   правильный source context; добавить contracts.json. Не выдавать setter macro
   за чтение; учитывать read-to-clear/W1C/FIFO/SR-DR side effects.
5. Выполнить collection и traceability без платы. Затем offline contract preflight
   в штатном runner выполняется до сервера; сам run уже аппаратная команда.
6. Объявить точный стенд, запустить один тест, изучить JSON/JUnit/GDB logs;
   только после проверки расширять набор. Зафиксировать восстановленное состояние.

Пример consumer уже содержит application function app_loop и соответствующие
CMSIS-макросы в ELF; в profile/Tests/board/test_blink.py:

```python
from stm32_gdbtest import case

@case("HW_CONSUMER_GPIO", labels=("gpio",), contracts=("consumer_gpio",))
def gpio(t):
    t.reach("app_loop")
    t.check("GPIOC clock", t.value("(RCC->AHB1ENR & RCC_AHB1ENR_GPIOCEN) != 0"), 1)
```

Запускать из корня модуля, указывая пути потребителя:

```powershell
python -B -m stm32_gdbtest collect --tests examples/minimal-consumer/profile/Tests/board
python -B -m stm32_gdbtest trace --tests examples/minimal-consumer/profile/Tests/board --requirements examples/minimal-consumer/profile/Tests/requirements.md
```

После сборки и согласования F411/ST-Link/SWD аппаратная команда (заменяет Flash,
если образ отличается; профиль другой платы не подставлять):

```powershell
python -B -m stm32_gdbtest run --session examples/minimal-consumer/build/debug/hwtest/session.json --test HW_CONSUMER_GPIO --stand path/to/stand.local.toml
```

check записывает результат и даёт FAIL при несовпадении. value возвращает int
из GDB-expression; неизвестный macro/символ даёт ERROR, а не ноль. reach проверяет
фактическую причину остановки; успешная установка breakpoint сама по себе не тест.
Измерение GPIO-регистра не доказывает напряжение на выводе, uwTick не измеряет
точную внешнюю длительность, Sleep под SWD не доказывает ток потребления.

Для агента задача должна содержать MCU, прошивку/ELF, стенд, цель и допустимые
воздействия. Не угадывать аппаратное соединение и не добавлять expected по
наблюдённому результату только ради PASS. Человек проверяет эти же допущения.
Все отрицательные сценарии сохраняют причину ERROR/FAIL; не подавлять исключения.

Внешние приборы/питание — отложенный интерфейс host-контроллера в TODO. Пока нет
стандартного API согласованного power-cycle/reconnect; не имитировать его скрытыми
вызовами из фонового GDB потока.
