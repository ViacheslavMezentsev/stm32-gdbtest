# call

[API](index.md) · [English](../../en/api/call.md)

`call(function, *args, this=None, signature=None, timeout=None) -> dict`; в `async def` — `await t.call(…)`

**Доступен с:** 0.3.0 · **API 3 (0.5.0):** в `async def` — `await t.call(…)`; новый параметр `timeout=` ограничивает вызов; вызов внутри выражений других методов отклоняется. [Правила sync/async](../LIVE_EXECUTION.md).

## Назначение

Вызывает функцию отлаживаемой программы на остановленном ядре и возвращает результат вызова.

## Контракт и ограничения

Аргументы передаются по значению: принимаются целые, конечные числа с плавающей точкой, логические значения; строки-выражения GDB не принимаются. Результат описывает `operation`, `function`, `arguments`, построенное `expression`, `outcome`, `return_value` и `return_state` (`available` или `void`), а вызов записывается в `mutations`.

`call(function, *args, this=None, signature=None, timeout=None)` поддерживает
явный объект и точную перегрузку в кандидате 0.6.0. В async def нужен await.
`this="&probe"` — адрес именованного объекта; `this="probe_ptr"` — именованный указатель.
Допускаются квалифицированные имена переменных. Поля, индексы, арифметика, cast и
вызовы в this пока не поддержаны. Указатель читается один раз; адрес объекта,
размер и выравнивание проверяются. Объект и память переменной-указателя должны
находиться в обычном окне SRAM 0x20000000–0x20100000 (верхняя граница исключена).
Это ограничение маршрута, не доказательство наличия/владения памятью или жизни объекта.
Сценарист обязан дойти до инициализации объекта и обеспечить безопасный контекст.

`signature="unsigned int(unsigned int) const"` задаёт результат, явные параметры
и квалификаторы метода. this в список параметров не входит; для нуля параметров — `()`.
Именованные типы/typedef разрешаются через GDB, сравниваются типы DWARF. Перегрузка
без signature остаётся ambiguous_function; несовпадение — signature_mismatch;
недопустимая грамматика — invalid_signature. Неоднозначный точный выбор тоже отклоняется.

Тип объекта должен точно совпадать; const/volatile не отбрасываются. Методу с this
нельзя передать объект другого типа (this_type_mismatch), отбросить квалификаторы
(this_qualifiers), передать null/MMIO/невыровненный адрес (invalid_this). this для
static/free даёт unexpected_this. Наследование, полиморфные типы, ref-qualified методы,
конструкторы/деструкторы, операторы и шаблонные имена не входят в поднабор.
Скалярные аргументы и результаты A4.1 сохраняются; явные Pointer/Reference описаны в A4.3a ниже. const-метод не гарантирует отсутствие побочных эффектов;
volatile-метод не получает транспортных гарантий MMIO.

Разрешение не исполняет код цели; затем вызывается ровно выбранный linkage-символ с
сохранённым значением this. В результате и mutations сохраняются this, this_address,
this_type, requested_signature, resolved_function и resolved_signature (по применимости).
При незавершённом dummy frame контекст не объявляется восстановленным; побочные эффекты
вызова автоматически не откатываются. Запрос в async остаётся ленивым до await.

Ограничения: вызов выполняется на остановленном ядре и меняет его состояние — побочные эффекты
функции сохраняются; без `timeout=` вызов ограничен только таймаутом сценария; результаты-указатели, числа с плавающей
точкой и переменное число аргументов в проверенный объём не входят.

## Пример

```python
result = t.call("app_step")
t.check("call returned a value", result["return_state"], "available")
```

Ошибка внутри вызванной функции возвращается как отказ операции, а не как исключение отладчика.

## Таймаут и async (0.5.0)

`timeout=` — секунды хоста, целая часть не меньше 1 и не больше остатка срока сценария; недостаточный
бюджет отклоняется до вызова (`operation_timeout`). Модуль включает `direct-call-timeout` и
`unwind-on-timeout` GDB. Прерванный вызов с dummy frame блокирует дальнейшее продолжение
(`call_incomplete`); очистка не восстанавливает контекст, повтора нет.

```python
@case("HW_CALL")
async def checksum(t):
    await t.reach("app_loop")
    result = await t.call("app_checksum", 7, timeout=2)
    t.check("checksum(7)", result["return_value"], 22)
```

Не рекомендуется: вызов функции внутри выражения `read`, `evaluate`, `write` или условия навигации —
он отклоняется (`expression_call_forbidden`); вызывайте функцию явно через `call`.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), разделы 4.8 и 4.23.

## Правильно и неправильно: возвращаемое значение

```python
result = t.call("poll", 110, timeout=2)  # async def: await t.call(...)
t.check("returned", result["outcome"], "returned")
t.check("value available", result["return_state"], "available")
t.check("DONE", result["return_value"], 2)
```

Неправильно: `t.check("DONE", t.call("poll", 110), 2)` сравнивает словарь с числом.
Не повторяйте call ради проверки значения: каждый вызов заново исполняет код цели.
`timeout` измеряется в секундах хоста; аргумент 110 — логические тики учебной модели.
Возврат 0 прикладной функции — не ApiError: применяйте check, а не refused.
[Пример с дефектами и восстановлением](../../../tests/logical-time/README.md).

## A4.1 — namespace/static

```python
result = await t.call("Probe::twice", 6, timeout=2)
t.check("twice", result["return_value"], 12)
```

В def уберите await. Пример проверяется без платы: [run_cpp.py](../../../tests/renode-backend/run_cpp.py).

## A4.2 — this / signature

```python
result = await t.call("Probe::choose", 2, this="&probe",
                      signature="unsigned int(int)", timeout=2)
t.check("selected overload", result["return_value"], 5)
```

## A4.3a — Pointer и Reference (кандидат 0.6.0)

`from stm32_gdbtest import Pointer, Reference`. Это неизменяемые описания, не адреса
и не выражения GDB; создание не обращается к цели. Разрешение происходит при call,
а в async — только при await, на остановленном ядре.

- `Pointer("samples", count=4)` — начало именованного массива; count не превышает размер из DWARF.
- `Pointer("buffer_ptr", count=4)` — именованная переменная-указатель; одно чтение значения на аргумент.
- `Pointer("&state")` — один именованный объект; count больше 1 отклоняется.
- `Pointer.null()` — явный null только для параметра-указателя; null из обычной переменной отклоняется.
- `Reference("state")` — существующий именованный объект, без временного объекта и пользовательского преобразования.

Count задаётся в элементах, по умолчанию 1; допустимы целые 1..1048576, не bool.
Для явного null count=0. Имя — до 256 символов, допустим namespace. Поля, индексы,
арифметика, casts и вызовы в путях не поддержаны. Ошибка описания — invalid_argument.

Поддержан один уровень T*/T& для целочисленных, bool и неполиморфных class/struct без
наследования. Проверяется точный тип; добавление const/volatile допустимо, снятие —
argument_qualifiers. Сигнатуры допускают эти типы и typedef; перегрузка выбирается
только явно. Для обычной C-функции описание также включает проверку DWARF.
T**, void*, function/member pointers, T&&, ссылки на массивы, объекты по значению и
указатели/ссылки в результате пока не поддержаны. Число не превращается в адрес.

До вызова проверяются размер, выравнивание и весь диапазон в обычной SRAM
0x20000000–0x20100000; память переменной-указателя проверяется перед чтением её значения.
Ошибки — argument_range, argument_type_mismatch, argument_qualifiers, unsupported_argument.
Для массива/объекта extent=known; для указателя extent=declared: это заявленная длина,
не доказательство выделения, владения или жизни памяти. Count НЕ ограничивает тело
функции и не связывается автоматически с другим аргументом длины. MMIO/Flash не допускаются.

В arguments сохраняется JSON-описание; argument_bindings содержит путь, фактический
и ожидаемый тип, адрес, count, bytes и extent. Для null — адрес/размер 0.
Модуль не добавляет снимок содержимого после вызова. Проверки изменения, соседних
данных и восстановления выполняются сценарием явно. Это не гарантия числа физических
доступов GDB-сервера; Reference передаётся выражением разыменования разрешённого адреса.
Все аргументы проверяются до единственного явного вызова; отказ не запускает функцию.

```python
from stm32_gdbtest import Pointer, Reference

result = await t.call("demo::sum", Pointer("samples", count=4), 4,
                      signature="unsigned int(const unsigned int *, unsigned int)", timeout=2)
t.check("sum", result["return_value"], 10)
await t.call("demo::bump", Reference("scalar"), signature="void(unsigned int &)", timeout=2)
```
