# План сохранения HAL-регрессии F030

[Документация](index.md) · [English](../en/F030_HAL_REGRESSION.md)

Подготовительный этап после [сверки HAL → CMSIS](F030_CMSIS_ACCEPTANCE.md).
Пример реализован в tests/hal-f030: автономная сборка и 17 сценариев.
Это offline-перенос, не новый HW PASS. ТЗ 0.38, п. 8.32/TC-129; API и схемы не изменены.

## Исходная база и размещение

Источник — [stm32-hwtest-blackpill, 0c8c966](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/tree/0c8c966f0429710e6e20472fbd9fe8898da7cfee).
Сохраняем один отдельный fixture `tests/hal-f030`, вне CMSIS `tests/firmware`
и вне ядра. Начальный перенос сохраняет все 17 сценариев, чтобы упрощение
прошивки не изменило доказательства незаметно. Сокращение — последующий этап.

| Источник в потребителе | Назначение при переносе |
| --- | --- |
| profiles/f030r8/Core, Platform, linker и IOC | Startup, инициализация и адаптер; IOC как происхождение, CubeMX не требуется при запуске CI |
| User/Inc/app.h, User/Src/program.cpp, adc_units.cpp | Существующий цикл, состояния и реакция на ошибки; сначала без переработки |
| profiles/f030r8/target.toml и tests/ | Identity, contracts, expectations, requirements и два файла сценариев |
| tests/scenarios/board.py, peripheral_runtime.py, power.py | Только используемые F030 сценарии; не импортировать исходный репозиторий |
| LICENSE и заголовки исходников | MIT приложения сохраняется; для ST-компонентов сохраняются их уведомления и лицензии |

CMake fixture должен явно перечислять исходники и подключать HAL/CMSIS из
закреплённого CubeF0 1.11.6. Не добавлять зависимость от stm32-cmake-yml,
абсолютных путей потребителя или нового скачивания во время offline-прогона.
Внешние ST-библиотеки не копировать в ядро. Отдельный build, ELF и manifest;
сборка `-Og -g3`, без LTO. Собственные новые каталоги lowercase.

## Какие доказательства нельзя потерять

| Сценарии исходного профиля | Критерий сохранения |
| --- | --- |
| HW_CLOCK, HW_GPIO, HW_BLINK | HAL/CMSIS выражения доступны в выбранном DWARF-контексте и проверяют фактическое состояние; не подменять все проверки числовыми масками |
| HW_ADC_DMA_INIT | Поля hadc/hdma_adc и независимые регистровые ожидания, scan16/17, normal halfword DMA |
| HW_TIM3_INIT | PSC7999, ARR99 и CEN=0 до запуска: CMSIS-проверка уже работающего таймера это не заменяет |
| HW_ADC_DMA_RUNTIME | Два callback, правильный указатель hadc, DMA exhausted, публикация двух последовательностей |
| HW_TIM3_IRQ, HW_RTC_ALARM | Естественные события, правильные callback handles, счётчики и публикация |
| HW_ADC_START_ERROR | force_return HAL_ERROR из HAL_ADC_Start_DMA → Error_Handler, ноль опубликованных последовательностей |
| HW_ADC_DMA_TIMEOUT | force_return void из callback после завершения DMA → deadline/Error_Handler; это подавление публикации, не неисправность DMA |
| HW_BOOT, HW_RTC_INIT, HW_ADC_UNITS, HW_ADC_INVALID, HW_ADC_VECTORS, HW_SLEEP_SYSTICK, HW_SLEEP_TIMER | Сохранить исходные проверки как контроль переноса; не заявлять точность датчика или измерение энергопотребления |

Начальные имена HAL-сценариев можно сохранить: разные CMake build/session
изолируют их от CMSIS. Не добавлять тестовые hooks, синтетические HAL-функции,
подмену handles или специальные ветви firmware ради удобства тестов.
После переноса контракты сверяются с реальными типами/макросами ELF. Новые
source-review hashes допустимы только после отдельного анализа исходников HAL.

## Последовательность веток

1. `codex/f030-hal-regression-plan` от `cea01f9`: этот документ, состав и приёмка.
2. Планируемая `codex/f030-hal-fixture`: автономная сборка, происхождение/лицензии,
   перенос 17 сценариев, manifest/trace/prepare; новые требования и TC в ТЗ.
3. Планируемая `codex/f030-hal-ci`: fixture в общей offline CI с явным ожидаемым
   набором; положительные и отрицательные contract checks. Linux и Windows,
   сначала GCC13; GCC14/15 не объявлять проверенными заранее.
4. Планируемая `codex/f030-hal-validation`: аппаратный протокол и решение о
   готовности переноса после исправления всех выявленных ошибок.

Ветки 2–4 зависимы; точные базы фиксируются по мере создания. Публикация пакетом
после локальных проверок; Docs/Offline каждого SHA, затем последовательный land.
Сам план не требует повторной сборки firmware. Gitlink потребителя обновляется
после принятия пакета. Старый HAL-профиль до этого не удаляется.

## Приёмка

- Fixture собирается из отдельного checkout модуля без исходного потребителя;
  manifest не содержит его путей. CI требует ровно 17 prepare, traceability и
  проверку contracts; отсутствующий тест — ошибка.
- Отдельно импортируются Python-сценарии на case-sensitive Linux: AST collection
  не доказывает разрешение импортов. Ошибочные contracts отклоняются до сервера.
- HW: NUCLEO-F030R8, родной ST-Link, SWD, OpenOCD; 17/17 на перенесённом ELF,
  JSON/JUnit для каждого сценария, точные SHA/GCC/HAL/backend и ограничения.
- После двух инъекций отдельно повторить нормальный ADC, TIM и RTC; проверить
  timeout/recovery штатного runner и восстановление. Первую ошибку сохранить,
  не скрывать автоматическими повторами. Перед набором подтвердить текущий стенд
  по принятому порядку; сейчас смена платы не требуется.
- В конце восстановить существующую HAL-прошивку потребителя и reset_run.
  Новый ELF не наследует старые аппаратные PASS.

Удаление HAL-профиля из потребителя — отдельное решение после публикации,
CI и аппаратной приёмки. Этот fixture сохраняет механизмы модуля на F0,
но не заменяет F1/F4 HAL-различия и регрессию будущего F411-consumer.

[Каталог техник TECH-001…008](TESTING_TECHNIQUES.md) — устойчивые ссылки из сценариев, условия сборки, ограничения и восстановление. При переносе HAL-сценариев сохранить ссылки TECH-001/003/004.

## Реализованный offline-этап (01.10.2026)

Ветка codex/f030-hal-fixture от main69cfb79. [Пример и команды](../../tests/hal-f030/README.md).
Сохранены Core/startup/linker и пользовательская firmware; Python helpers
локализованы в hal_scenarios, неиспользуемый F1/F4 rcc_error не переносится.
TECH-001/003/004/007 ссылаются на руководство. Provenance содержит исходный SHA,
пути и нормализованные LF-хеши; hardware результаты не наследуются.

Windows GCC13: build, CTest19/19 (17 prepare + trace + fixture) PASS;
docs/format/host5/5 PASS (host97,8 skips). Linux GCC13: изолированный снимок
модуля без потребителя, build и CTest19/19 PASS, docs/host4/4 PASS.
Отчёты: build/hal-fixture-check внутри модуля. В локальном Linux-образе
нет clang-format: первый запуск format ERROR сохранён в истории работы;
формат проверен Windows clang-format, Linux format не заявлен PASS.
Исходные пробелы/пустые строки ST/CubeMX сохранены, поэтому git diff --check
для импортированных файлов выдаёт прежние whitespace замечания.

Общий CI пока не запускает сборку HAL fixture: следующий этап — отдельная
ветка CI с явным ожидаемым набором и отрицательными контрактами. HW17/17,
положительные повторы после инъекций и timeout/recovery ещё не выполнены.
Исходный HAL-профиль потребителя не удалён, firmware на плате не менялась.

## CI-этап (01.10.2026)

codex/f030-hal-ci от a3898ff добавляет обязательный уровень hal в Offline.
[Состав проверки и локальный запуск](testing.md#hal-f030-в-offline-ci).
HAL F0 взят из gitlink CubeF0: 0cf0218694f30a90d11ff9e53c1908bf9e745443.
Новый закреплённый Docker-образ успешно собран и прошёл verify environment.
В изолированной Linux-файловой системе без сети полный набор15/15 PASS:
docs3 + format1 + host1 + CMSIS9 + HAL1. HAL:19 CTest,17 свежих prepare JSON,
положительный preflight и5 отрицательных контрактов. Windows: docs/format/host/hal6/6.
ТЗ0.39/TC-130, API и runtime ядра не изменены.

Отчёты модуля: build/hal-ci-check/ci/summary.json, hal-results/ci.log,
hal-results/junit.xml, hal-results/contracts/*.result.json; образ — build/hal-ci-image.log.
GitHub CI этого SHA ещё требуется после push; новый HW-прогон не выполнялся.
Предыдущий a3898ff прошёл Docs и все5 jobs Offline до добавления HAL CI.
Старое утверждение выше «общий CI не запускает fixture» относится к этапу0.38.
