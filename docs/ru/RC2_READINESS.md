# Подготовка stm32-gdbtest 0.1.0-rc.2

[Документация](index.md) → Подготовка rc.2 · [English](../en/RC2_READINESS.md)

Согласованный состав кандидата, 01.10.2026. База main `7f3c65b`; это план
приёмки, не утверждение о выпущенном rc.2. Документальный аудит принят в main `eaf31ea`; выпускная ветка
`codex/release-0.1.0-rc.2` сообщает `0.1.0rc2`. Тег ещё не опубликован.

## Что входит

- Исправления после rc.1: manifest с CMake 3.25, HAL macro preflight для C++
  и отсутствующих DWARF-типов, J-Link mapping STM32F103CBT6.
- CMSIS F030: 18 сценариев, таймер/IRQ, ADC/DMA, численные векторы,
  RTC, Sleep/WFI и выбранные отказные ветви.
- Отдельный tests/hal-f030: 17 сценариев исходного HAL-приложения,
  provenance/лицензии, build/prepare и отрицательные контракты в CI;
  воспроизводимая HW-приёмка с восстановлением прошивки.
- Каталог TECH-001…008, lowercase tests с чтением прежнего Tests,
  локальные remote.toml и уточнённые инструкции.

F103/F411 в tests/firmware сохраняют по два базовых сценария boot/GPIO.
examples/minimal-consumer остаётся примером подключения F411. Полный перенос
периферии F103/F411/F401/F429, RISC-V, QEMU/Renode, внешнее оборудование,
многоядерность, Python-пакет и оптимизация CI не входят в обязательный состав rc.2.
API_VERSION=1 и схемы сохраняются, если аудит не обнаружит необходимого изменения
контракта; такое изменение потребует отдельного решения и миграции.

## Последовательность и критерии

1. **Сверка документации**, codex/rc2-docs-audit: актуальные руководства и планы
   согласованы с кодом, даты и результаты отделены от истории, RU/EN согласованы.
   Версию не менять, старое описание тега rc.1 не редактировать.
2. **Выпускная ветка** от принятого main: Python 0.1.0rc2, раздел CHANGELOG
   0.1.0-rc.2 в обеих локализациях, новая ревизия ТЗ к выпуску, README/API/STATUS
   и docs/releases/v0.1.0-rc.2.md. До приёмки описание явно является черновиком.
3. **Offline** на опубликованном SHA: Docs и все пять jobs Offline; CMSIS
   девять сочетаний MCU/GCC, HAL GCC13, host/format/contracts и артефакты.
4. **Аппаратная приёмка** кандидата по таблице ниже. Первый неожиданный результат
   сохранять; исправление создаёт новый SHA и требует повторной затронутой проверки.
5. **Потребитель**: подключить кандидата настоящим gitlink, повторить build/prepare
   и согласованные HW/recovery-проверки; изменения потребителя публиковать отдельно.
6. **Публикация**: сверить финальный SHA, CI, протоколы и текст выпуска; владелец
   выполняет land, затем подписанный аннотированный тег v0.1.0-rc.2 и GitHub prerelease.
   До финальной сверки команды публикации тега не выполнять.

| Стенд / режим | Обязательное доказательство rc.2 | Статус |
| --- | --- | --- |
| NUCLEO-F030R8, native ST-Link/SWD, OpenOCD, Windows | Единый набор 18 CMSIS-сценариев; отдельно цикл записи/identity/full-image/verify-only/timeout/recovery | 5b7b466: CMSIS 18/18, lifecycle 10/10, restore PASS |
| Та же Nucleo, HAL fixture | 17 сценариев, 6 положительных повторов, timeout/recovery и restore | 5b7b466: 17/17 + 6 repeats, timeout/recovery/restore PASS |
| WeAct BluePill-Plus F103C8, J-Link/SWD, Windows | Базовые сценарии и цикл runner с recovery | 5b7b466: 10/10, restore PASS |
| BlackPill F411CE, ST-Link/SWD, OpenOCD и ST GDB Server, Windows | Базовые сценарии и цикл runner с recovery для обоих backend | 5b7b466: OpenOCD 10/10; ST USB ERROR + reconnect, continuation PASS |
| Windows → Orange Pi 5 по SSH; pack/run --package; Hardware workflow | Повтор согласованной удалённой матрицы, пакеты того же кандидата | 5b7b466: Hardware 36788964902 PASS; 27 JSON verified |

tests/firmware/run_hw.py проверяет жизненный цикл runner через boot/GPIO.
Он не запускает автоматически все 18 F030-сценариев: полный набор выполнять
отдельно через штатные CLI/CTest с явным stand и внешним timeout.
Аппаратные команды меняют Flash. Перед каждым набором назвать стенд;
после набора восстановить согласованную прошивку и подтвердить reset_run.

Недоступный Linux-стенд не заменять прежним PASS: зафиксировать ограничение и
согласовать сокращённую матрицу rc.2 до публикации. Наличие старого результата
не является новой проверкой; дополнительные платы не объявлять проверенными.

## Сверка документации

Область — все отслеживаемые Markdown-файлы модуля, включая RU/EN, examples,
requirements, лицензии и описание прежнего релиза. Структурная проверка охватывает
файлы ссылок и языковые пары; она не подтверждает семантику всех внешних URL,
якорей или команд на неподключённом оборудовании.

| Группа | Источник истины / действие |
| --- | --- |
| README, index, STATUS, TODO, CHANGELOG | Состав main и результаты CI/HW; убрать устаревшие будущие шаги из текущего статуса |
| API, GETTING_STARTED, TEST_AUTHORING, CONTRACTS, HAL_MACRO_GUIDE | CLI help, CMake attach, Target API, contracts и реальные каталоги tests; совместимость Tests сохранить |
| testing, HARDWARE_CI, LINUX_STAND, HOWTO, maintenance | workflows, run_checks, run_hw, stand tooling; различать offline, HW и доступность стенда |
| BACKENDS, DEBUGGER_OWNERSHIP, TARGET_IDENTITY, IMAGES, MANIFESTS | Реализация backend/locks/image/manifest и host-проверки; неподдержанные возможности не добавлять по аналогии |
| CMSIS_MIGRATION, TESTING_TECHNIQUES, F030-протоколы | Текущий inventory сценариев и датированные отчёты; история остаётся историей |
| VERSIONING, ТЗ, releases | Версия из __init__, согласованные критерии и доказанный SHA; опубликованные заметки rc.1 неизменны |
| SOURCE, лицензии, example README и requirements | Происхождение, сохранённые лицензии и фактические команды/ID; тестовые hooks не добавлять |

## Текст тега и страницы Releases

Канонический текст — docs/releases/v0.1.0-rc.2.md, RU затем EN, в формате
[VERSIONING](VERSIONING.md). Один и тот же файл используется как сообщение
подписанного тега (--cleanup=verbatim) и описание GitHub prerelease.
Текст должен различать новые функции, исправления, миграцию и ограничения;
указывать Python-версию/API/ТЗ и ссылки на проверенную матрицу.

Нельзя заранее вписывать PASS, подменять runtime SHA хешем последующей правки
документации или пытаться включить собственный SHA коммита внутрь этого же коммита.
SHA аппаратно проверенного кода хранить в протоколе; финальный SHA тега получать
из Git при проверке публикации. Для последующей правки только текста явно сверить
отсутствие изменений кода/firmware и повторить проверки документов/CI нового SHA.
Если меняются код, профиль, toolchain или сценарии — повторить затронутую HW-приёмку.
Опубликованный тег не перемещать; несоответствие перед публикацией сначала исправить.

## Предварительная проверка окружения (не HW-приёмка rc.2)

01.10.2026: владелец подтвердил три стенда на Orange Pi. Doctor через SSH
для F030/ST-Link/OpenOCD, F103/J-Link и F411/ST-Link/OpenOCD завершился без
FAIL/WARN: инструменты, USB serial и права доступа соответствуют конфигурациям.
Служба Runner.Listener работает; выполнение Hardware workflow пока не проверено.
GDB-серверы не запускались, MCU не подключались, Flash не менялась.
Локальные отчёты: build/rc2-readiness/*-doctor.json; TOML *-remote.toml исключены из Git.

Сверка документации: 86 Markdown-файлов, 57 внутренних ссылок с якорями — без
ошибок; docs/spec/links/pairs на Windows и Linux Docker — 3/3 на каждой ОС.
Код, firmware и опубликованный текст rc.1 не менялись. ТЗ — ревизия 0.41;
финальная приёмка TC-132 и выпускная ревизия ТЗ ещё впереди.

## Локальная подготовка выпускной ветки (01.10.2026)

Python 0.1.0rc2, API_VERSION=1, ТЗ 0.42. Windows docs/host 4/4 PASS.
Linux Docker: docs/format/host и девять CMSIS сочетаний прошли (14 этапов).
HAL первоначально отклонён CMake из-за Windows cache в build/ci-gcc13; каталог
сохранён как ci-gcc13-windows-before-rc2. На чистом build отдельный HAL-прогон
1/1 PASS: 19 CTest, 17 prepare и отрицательные контракты. Это два прогона,
не единый 15/15. Отчёты: build/rc2-offline-initial.json и build/rc2-offline-hal.json.
Опубликованный SHA ещё должен пройти Docs/Offline. HW-приёмка кандидата и
обновление потребителя остаются открытыми; текст релиза — черновик.

## Ошибка приёмки rc.2 (01.10.2026)

Docs и весь Offline для e3f5233 прошли. Windows GDB → SSH/OpenOCD на Orange Pi,
NUCLEO-F030R8/ST-Link: 6 PASS, затем HW_CI_TIM3_IRQ ERROR; серия остановлена.
TIM3_IRQHandler достигнут, ICSR=32. Диагностика подтвердила: xPSR — Bad register,
xpsr — доступен. Сервер: xPack OpenOCD 0.12.0+dev-02228-ge5888bda3-dirty.
GDB работает на Windows. Исходный HAL восстановлен, HW_BOOT/HW_BLINK PASS, reset_run.
Отчёты: build/rc2-acceptance/f030-full-20260930T221717Z/summary.json.

Исправлены сценарии: SCB ICSR VECTACTIVE с preflight CMSIS-макросов.
Firmware и runtime не меняются; требуется повтор полного набора и CI нового SHA.
core_registers профиля остаётся серверозависимым: diagnostic_errors сохраняет
недоступный xPSR. Это ограничение диагностики, не отсутствие IRQ.

Повтор на 8a7928c: 14 PASS, RTC_ALARM ERROR после перехода в app_loop — SCB вне DWARF-контекста app.c. Восстановление HAL boot/blink PASS. Адрес ICSR и маска теперь сохраняются в RTC_IRQHandler до перехода (TECH-002). Отчёт: build/rc2-acceptance/f030-full-20260930T222249Z/summary.json.

## Повтор CMSIS на исправленном коммите

Runtime/scenario SHA: a48158cbfc8c61e015f5e84daa494ce66f639ce0. Единая серия
18/18 PASS, затем восстановление исходного HAL: HW_BOOT/HW_BLINK PASS, reset_run.
Windows xPack GCC13/GDB, ST-Link/SWD, OpenOCD на Orange Pi через SSH.
ELF SHA256: 6a5ed3b0835ce5f093e808fcca6cce453399d1ad8d3e130816647c5d3afb8280.
Отчёт: build/rc2-acceptance/f030-full-20260930T222540Z/summary.json.
Перед ним запуск 20260930T222451Z прерван локальным сборщиком отчётов: одновременно
выполнявшийся CTest prepare записал дополнительные result.json в тот же out.
HW_ADC_INIT был PASS; восстановление PASS. Этот запуск не засчитывается как
полный набор; повтор выполнен последовательно, без изменений кода.
Offline F030 19/19, docs/host 4/4. Новый опубликованный SHA ещё требует Docs/Offline.
Это SSH-проверка, она не заменяет отдельную локальную Windows/backend матрицу.

## HAL F030 на том же кандидате

На a48158c: 17/17 сценариев, шесть положительных повторов после инъекций ADC,
ожидаемый timeout ERROR после входа в loop, host recovery reset_run и повтор ADC PASS.
Затем исходный HAL потребителя восстановлен: HW_BOOT/HW_BLINK PASS, MCU running.
Среда та же: Windows GCC13/GDB → SSH/Orange Pi/OpenOCD, NUCLEO-F030R8/ST-Link.
Отчёт: tests/hal-f030/build/validation/20260930T222705.675442Z/summary.json.
Offline HAL: 19/19. Pack/Hardware workflow, циклы full-image/identity и оставшиеся
локальные/удалённые стенды ещё не приняты. Исправления сценариев требуют нового CI;
тег и land пока не выполнять. Последующие документальные коммиты не заменяют
указанный SHA фактически выполненных сценариев.

## Цикл runner через SSH (01.10.2026)

Проверенный SHA: 873f1ac29f5c85b2049c10be773c8486a35c545c. Docs и все пять
Offline jobs SUCCESS (Docs 36786189561, Offline 36786189557).
Windows GCC13/GDB, GDB-серверы на Orange Pi; SWD, без дополнительных соединений.

| Стенд | Этапы | Восстановление | Каталог в build/rc2-acceptance |
| --- | --- | --- | --- |
| NUCLEO-F030R8 / ST-Link / OpenOCD | 10/10 | HAL boot/blink PASS, reset_run | f030r8-lifecycle-20260930T223538Z |
| WeAct BluePill-Plus F103C8 / J-Link | 10/10 | HAL boot/blink PASS, reset_run | f103c8-lifecycle-20260930T223631Z |
| BlackPill F411CE / ST-Link / OpenOCD | 10/10 | HAL boot/blink PASS, reset_run | f411ce-lifecycle-20260930T223716Z |

Это 10 этапов проверки, не 10 положительных аппаратных сценариев:
build, prepare, boot, GPIO, strict identity, full-image A5, verify-only FF
(ожидаемый ERROR без записи), full-image FF, timeout (ожидаемый ERROR с recovery),
GPIO после recovery. После каждого набора отдельно восстановлена прошивка
потребителя и проверены boot/blink. Каждый этап вызван штатным run_hw.py отдельно;
его summary/log/policy сохранены перед следующим вызовом, результаты CLI остались
в build профиля. Обвязка прекращает серию на первом неожиданном результате.

Также pack F030 подготовил 18 сценариев из проверенного ELF. Запуск пакета
на Linux и Hardware workflow пока не подтверждены. Конфигурация F030 в домашнем
каталоге runner на Orange Pi всё ещё выбирает J-Link; перед workflow владелец
должен переключить её на родной ST-Link/OpenOCD. Локальный remote.toml использовал
правильный ST-Link и не зависел от этого файла. Локальная Windows/backend матрица,
подключение потребителя и окончательный текст выпуска остаются впереди.

## Hardware workflow: результат и потеря отчётов

На 759840a: Hardware 36787681339, prepare/hardware SUCCESS. Сборка пакетов в GitHub Ubuntu, выполнение на Orange Pi Linux aarch64. Три summary и журнал: по 10/10. Однако open_package удалял предыдущие runs при каждом открытии: в артефактах осталось по одному after-recovery JSON. Эти данные подтверждают журнал выполнения, но не полную сохранность доказательств; приёмка требует повторения после исправления.

Локальный архив: build/rc2-acceptance/hardware-36787681339/hw; восстановление: restore.json — boot/blink PASS для всех трёх исходных HAL, reset_run. F030 stand на runner исправлен владельцем на ST-Link/OpenOCD. Платы оставлены работающими. Новое исправление проверяется TC-133, затем Offline/Hardware на новом SHA.

Локальная проверка исправления: Windows docs/host 4/4; Linux Docker host 1/1; 98 host-тестов (Windows — 8 платформенных skips). Два последовательных CLI prepare одного F030-пакета сохранили оба JSON в отдельных sessions. Аппаратный повтор исправления пока не выполнен.

## Приёмка 5b7b466: пакеты и локальные стенды (01.10.2026)

SHA кода: 5b7b4661a27db497f74f475de667b8df731e9c99. Docs 36788642783,
Offline 36788643033 и Hardware 36788964902 — SUCCESS. Hardware собрал пакеты
в GitHub Ubuntu и выполнил их на Orange Pi Linux aarch64: по 10/10 этапов
F030/OpenOCD, F103/J-Link, F411/OpenOCD. Проверены все 27 отдельных JSON,
их соответствие summary, ожидаемые ERROR verify-only/timeout и recovery.
Скачанный владельцем hardware-results.zip содержит те же 27 JSON побайтно.
Первоначальный сетевой отказ скачивания ZIP с Windows не был ошибкой workflow.
Локальные доказательства: build/rc2-acceptance/hardware-36788964902, audit.json,
github-audit.json и restore.json. Исходные HAL восстановлены, boot/blink PASS.

Владелец перенёс три стенда на Windows, сохранив SWD. На том же SHA:

| Стенд / набор | Результат | Доказательства |
| --- | --- | --- |
| NUCLEO-F030R8 / ST-Link / OpenOCD, CMSIS | 18/18; restore boot/blink PASS | f030-windows-full-20260930T230819Z |
| Та же Nucleo, lifecycle | 10/10; restore PASS | f030r8-windows-nucleo-f030r8-20260930T230946Z |
| Та же Nucleo, HAL | 17/17, 6 повторов, ожидаемый timeout ERROR, recovery, ADC после recovery, restore PASS | 5b7b466: 17/17 + 6 repeats, timeout/recovery/restore PASS |
| WeAct BluePill-Plus / F103C8 / J-Link | 10/10; restore PASS | f103c8-windows-bluepill-jlink-20260930T231215Z |
| BlackPill / F411CE / ST-Link / OpenOCD | 10/10; restore PASS | f411ce-windows-blackpill-20260930T231302Z |
| Та же F411, ST GDB Server 7.14 | 8 этапов PASS, затем USB ERROR до ready; после reconnect boot, timeout/recovery и after-recovery PASS, restore PASS | f411ce-windows-blackpill-stlink-20260930T231349Z и 20260930T231636Z |

Каталоги без полного префикса находятся в build/rc2-acceptance; в каждом summary.json.
ST server — не непрерывный 10/10: исходный timeout не начался, восстановление
через ST и OpenOCD тоже отказало. ST сообщил Target USB comms error; OpenOCD
прочитал некорректные сведения STLINK V8J0S0 / VID:PID 0000:0001. После ручного
USB reconnect связь и HAL boot/blink восстановились; затем boot подготовил
CMSIS-образ для оставшихся двух этапов, и HAL снова восстановлен.
Причина не установлена; reconnect не является исправлением runtime или
доказательством устойчивости длительной серии. Не скрывать это ограничение в релизе.

Все три платы оставлены на Windows, исходный HAL running. Подключение кандидата
потребителем, финальная сверка документации/текста выпуска и проверка итогового
SHA остаются открытыми. Последующие изменения только документации не заменяют
этот SHA аппаратно проверенного кода.

## Интеграция потребителя и условия публикации

Потребитель stm32-hwtest-blackpill: fb2d18626a3c9ff831bd8d2a0c58bb97c6150cbd,
закреплён модуль 67b7431eabba970ed2f690fb5ac2fcec045cc06e (только документация
относительно аппаратно проверенного 5b7b466). GitHub Offline
[36791792481](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/actions/runs/36791792481)
— SUCCESS: пять профилей, 120 CTest, в том числе 105 prepare.
Локально Linux Docker — те же 120/120; Windows F411 — 25/25 host/prepare.
F411/ST-Link/OpenOCD под Windows через CLI потребителя: 22/22 сценария;
отдельно ожидаемый timeout ERROR с подтверждённым входом в цикл,
host recovery, затем ADC DMA, boot и blink PASS. Исходная HAL-прошивка running.
Доказательства потребителя: build/rc2-integration/linux-reports/summary.json,
windows-host.log, f411-20260930T232546Z/summary.json и recovery/summary.json.

Остаётся проверить Docs и полный Offline окончательного документального SHA,
согласовать land модуля, обновить gitlink потребителя и проверить его новый CI.
Затем владелец выполняет land потребителя и публикацию подписанного тега/
GitHub prerelease. Тег не создан; описание выпуска подготовлено для проверки.

Публикация завершена: v0.1.0-rc.2 → a0d6547, подписанный тег Verified,
GitHub prerelease и текст тега совпадают с docs/releases/v0.1.0-rc.2.md.
Потребитель main2b9d75f закрепляет этот SHA, Offline36797076345 SUCCESS.
Исторические открытые этапы выше завершены; тег не изменяется.
