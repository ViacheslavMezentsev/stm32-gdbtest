# Написание тестов человеком и ИИ-агентом

[Документация](index.md) → Написание тестов · [English](../en/TEST_AUTHORING.md)

Процесс одинаков для ручной работы и генерации агентом. Человеку достаточно
редактора Python или VS Code и команд ниже; агент не является зависимостью.

Для агента это замкнутый контур: он формулирует требование, пишет сценарий в
репозиторий, проверяет его без оборудования (`run --prepare-only`), запускает на
стенде и читает `result.json`. Результат — не ответ в чате, а тестовый кейс проекта,
который потом выполняется снова вручную, в CI или на стенде в цикле. Агент не меняет
стенд, прошивку отладчика и опасные настройки Flash без согласования с владельцем
([сопровождение](maintenance.md#работа-с-оборудованием)).

1. Сформулировать наблюдаемое требование и его ID в `Tests/requirements.md`.
   Определить допустимое влияние halt/reset и критерий ошибки.
2. Подготовить `target.toml` по конкретному MCU, плате и прошивке: Flash, identity,
   бюджет точек останова, fault handlers. Собрать Debug с `-g3`, проверить ELF и manifest.
3. Написать функцию верхнего уровня в `profile/Tests/board/test_*.py`. Модуль не
   изменяется ради проектного сценария; вспомогательный код хранится в проекте.
4. Если используются HAL- или CMSIS-макросы, выбрать чистые getter и predicate
   выражения и контекст — функцию из единицы компиляции, где макрос определён;
   добавить `contracts.json`. Не выдавать setter за чтение; учитывать read-to-clear,
   W1C, FIFO и последовательности SR/DR ([HAL-макросы](HAL_MACRO_GUIDE.md)).
5. Без платы: сбор и traceability, затем `run --prepare-only` — он выполнит
   offline-проверку контрактов, manifest и образа до GDB-сервера.
6. Объявить точный стенд, запустить один тест, изучить JSON, JUnit и журналы GDB;
   только после этого расширять набор. Зафиксировать восстановленное состояние.

Пример потребителя уже содержит функцию `app_loop` и CMSIS-макросы в ELF;
`profile/Tests/board/test_blink.py`:

```python
from stm32_gdbtest import case

@case("HW_CONSUMER_GPIO", labels=("gpio",), contracts=("consumer_gpio",))
def gpio(t):
    t.reach("app_loop")
    t.check("GPIOC clock", t.value("(RCC->AHB1ENR & RCC_AHB1ENR_GPIOCEN) != 0"), 1)
```

Ещё три примера на Cortex-M0, M3 и M4 — CI-прошивки `Tests/firmware/profiles/*`.

Из корня модуля, с путями потребителя:

```powershell
python -B -m stm32_gdbtest collect --tests examples/minimal-consumer/profile/Tests/board
python -B -m stm32_gdbtest trace --tests examples/minimal-consumer/profile/Tests/board --requirements examples/minimal-consumer/profile/Tests/requirements.md
python -B -m stm32_gdbtest run --session examples/minimal-consumer/build/debug/hwtest/session.json --test HW_CONSUMER_GPIO --prepare-only
```

После сборки и согласования стенда F411/ST-Link/SWD — аппаратная команда (записывает
Flash, если образ отличается; профиль другой платы не подставлять):

```powershell
python -B -m stm32_gdbtest run --session examples/minimal-consumer/build/debug/hwtest/session.json --test HW_CONSUMER_GPIO --stand path/to/stand.local.toml
```

`check` записывает результат и даёт FAIL при несовпадении. `value` возвращает `int`
из выражения GDB; неизвестный макрос или символ даёт ERROR, а не ноль. `reach`
проверяет фактическую причину остановки: успешная установка точки останова сама по
себе не тест. Значение регистра GPIO не доказывает напряжение на выводе, `uwTick` не
измеряет точную внешнюю длительность, Sleep под SWD не доказывает ток потребления.

Задача для агента должна содержать MCU, прошивку или ELF, стенд, цель и допустимые
воздействия. Не угадывать аппаратное соединение и не подставлять ожидания по
наблюдённому результату ради PASS; человек проверяет те же допущения. Отрицательные
сценарии сохраняют причину ERROR или FAIL; исключения не подавляются.

Внешние приборы и питание — отложенный интерфейс host-контроллера
([дорожная карта](../../TODO.md)). Стандартного API power-cycle и reconnect пока нет;
не имитируйте его скрытыми вызовами из фонового потока GDB.
