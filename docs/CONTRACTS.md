# ELF/HAL-контракты

Сценарий объявляет имена контрактов литерально в `@case(..., contracts=("name",))`.
Определения — Tests/contracts.json в PROFILE_DIR. Не запрошенные контракты дают
NOT_REQUESTED в metadata, а не доказательство совместимости и не результат SKIP.

## Порядок и разделение ответственности

1. Раннер копирует ELF и проверяет build manifest.
2. Загружает только запрошенные контракты. Неизвестное имя или схема — ERROR.
   Для `source_reviews` сравнивает хеши с входами проверенного build manifest.
3. Сохраняет выбранные декларации, SHA-256 реестра и `contract-request.json`.
4. Запускает отдельный batch GDB с этим ELF, отключённым auto-load, без сервера
   и без target connect. Внешний timeout — 15 секунд. Проверки используют только
   Symbol/Type/Block и list/info macro/macro expand, не parse_and_eval, inferior calls
   или запись памяти.
5. Принимает `contract-result.json` только при PASS, коде выхода 0 и совпавшем ELF SHA.
   Ошибка, отсутствие результата или timeout останавливают запуск до GDB-сервера.
6. После успешного preflight выполняет обычный аппаратный сценарий с прежними
   identity/Flash/reset/breakpoint/teardown проверками. Результаты preflight включены
   в `result.json` и JUnit; отдельный журнал — `contract-preflight.log`.

Общий механизм находится в [contracts.py](../stm32_gdbtest/contracts.py); MCU/HAL ожидания — в профиле,
проектные сценарии — у потребителя. Изменение контракта не требует пересборки
прошивки: это ожидание теста, его выбранный снимок сохраняется отдельно от сборки.

## Что задаёт schema 1

- `functions`: глобальные функции, тип возврата и **упорядоченный список** arguments
  с name/type. Проверяются число, порядок типов, имена аргументов и их типы в блоке.
- `type_context`: имя функции из functions для разрешения fields/enums.
- `fields`: необходимые именованные поля структур и их типы; лишние поля допустимы.
- `enums`: необходимые enum-константы и числовые значения; лишние значения допустимы.
- `source_reviews`: файл, SHA-256 и reason ручного анализа используемого поведения.

Типы аргументов/возврата разрешаются в блоке самой функции. Глобальный lookup_type
дал ложное несовпадение GPIO_TypeDef между C и C++ compilation units. Сравнение
строковых имён не исправляет проблему: используется равенство GDB Type в нужном
контексте. fields/enums используют явный type_context, независимо от порядка JSON.
Поддерживаются именованные типы, `const Type` и указатели с написанием `Type *`; не реализован
универсальный C/C++ parser для массивов, шаблонов и function pointers.


## Границы доказательства

Перед NULL-инъекцией необходимо изучить используемый исходник HAL и закрепить его
hash в source_reviews. Не обновлять hash механически ради PASS. Наличие сигнатуры
не доказывает семантику тела, транзитивных заголовков и effective macros.
force_return пропускает тело функции; такой тест проверяет реакцию вызывающего кода.
Callback signature не доказывает IRQ-маршрут, DWARF-аргумент — доступность значения
при halt. Optimized-out и pending breakpoints проверяются отдельно в runtime.

Контракт macros с обязательными context/expressions описан в
[HAL_MACRO_GUIDE](HAL_MACRO_GUIDE.md). Preflight раскрывает, но не вычисляет выражения.
Проверки source_reviews опираются на [build manifest](MANIFESTS.md).

[Профильные контракты и offline-регрессия](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/HAL_CONTRACTS.md) остаются у стенда.
