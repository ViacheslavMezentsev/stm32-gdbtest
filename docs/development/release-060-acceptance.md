# A8 — кандидат и матрица приёмки 0.6.0

[План 0.6.0](release-060-plan.md) · [Приёмка 0.5.0](release-050-acceptance.md) · [Памятка](../../TODO.md)

Кандидат кампании — main `6530395db303afb7b9f5fc85743501aa7009c47e` (подписан, A0–A7.5).
Версия пакета на нём ещё 0.5.0; выпускной коммит меняет только номер версии и документы
(правило 4 приёмки 0.5.0), его проверки перечислены в конце. Потребители: BluePill `7023d1b`,
BlackPill `de37b67` (gitlink `a7b0951`); в кампании C1–C3 подмодуль в рабочей копии — на кандидате.

Запуски Windows — локальный мост к рабочему месту (Windows 11, Python 3.11.9, CMake/CTest 4.4,
Ninja 1.13, xPack GCC/GDB 14.2.1-1.1 c GDB 15.2.90 и Python 3.12.8, Renode 1.17.0, QEMU 11.1,
OpenOCD 0.12.0, для AT32 — OpenOCD Artery с J-Link). Linux — облачный контейнер агента (Ubuntu
24.04 x86_64, Python 3.11, тот же xPack 14.2.1, Renode 1.17.0 portable, QEMU 8.2.2, clang-format
18.1.8). Время — UTC+5, 28.10.2026: офлайн 21:48–22:25, платы 22:19–23:28.

## Итог

| ID | Статус | Факт |
| --- | --- | --- |
| G0 | PASS | Кандидат и потребители подписаны, деревья чистые, ветки влиты владельцем; CI этих SHA подтверждает владелец |
| O1 | PASS | Host 879 тестов: Windows — OK, 14 пропусков; Linux — OK, 6 пропусков (Windows-специфичные) |
| O1b | PASS | Документация 5/5 (spec, api-spec, links, pairs, public); clang-format 18 — PASS |
| O2 | PLANNED | Docker volume у владельца (необязательно: O1/O1b и E1–E6 выполнены на обеих ОС) |
| E1 | PASS | renode-backend 25/25 ожидаемых исходов (11 PASS, 2 FAIL, 11 ERROR, 1 SKIP) — по два запуска на Windows и Linux |
| E1a | PASS | A1–A4 в Renode, Windows и Linux: report 18/18 и --summary 36/36, journal 20/20, report quota 32/32, C++ call 9/9 (8 PASS, намеренный ERROR точки внутри call) |
| E2 | PASS | qemu-backend 7/7 (4 PASS, 1 FAIL, 2 ERROR), по два запуска на Windows и Linux |
| E3 | PASS | mmio-renode: PASS и negative-control, Windows и Linux |
| E4 | PASS (renode-cache Linux — NOT_APPLICABLE) | live-observer: ожидаемые исходы на обеих ОС; renode-cache на Windows: host и Renode PASS, negative-control FAIL (ожидаемо) |
| E5 | PASS | A5 в Renode, Windows и Linux: controlled-input 12 (8 PASS, 2 FAIL, 2 ERROR; анализ 12 PASS, восстановление 12 VERIFIED), modeled-gpio PASS, buffer-consumption 14 (10/2/2, 14 VERIFIED), logical-time, counter-cost, stateful-buffer PASS |
| E6 | PASS | A6 офлайн, обе ОС: rosbag-import 23/23 (3 PASS, 1 FAIL, 19 UNKNOWN), external-capture 19/19 (2 PASS, 2 FAIL, 15 UNKNOWN) |
| D1 | PASS | Квалификация DDTT на хосте и в Renode, Windows и Linux |
| K0 | PASS | Комплекты плат собраны и проверены в Renode до доступа к оборудованию: H2 90/90 (шесть профилей), новый H5 48/48 |
| H1 | PASS | MMIO GPIO/DMA на шести MCU: 141/141 (F411CE, F401CC, F429ZI по 24, F103, F030R8, AT32F403A по 23), восстановление VERIFIED, полные Flash/SRAM и регистры ядра совпали. F411: первая попытка отказала без воздействия («clock disabled; no blind ungating» — у исходной прошивки выключен тактовый сигнал), повтор с прошивкой потребителя BlackPill |
| H2 | PASS | Async API 3 и ограниченный call на шести MCU: 6×15 = 90/90 ожидаемых исходов, независимый аудит 6×41 = 246/246, postcheck VERIFIED |
| H3 | PASS | VTOR/FPB на F411: 12/12 ожидаемых исходов (8 PASS, 3 ERROR, 1 FAIL), recovery VERIFIED; независимый postcheck: Flash совпала, FPB/VTOR/NVIC равны снимку до опыта |
| H4 | PASS | HAL F030: 41 этап (40 PASS и ожидаемый ERROR timeout с восстановлением), исходный HAL-образ восстановлен |
| H5 | PASS | Новое для 0.6.0, на шести MCU (M0, M3, три M4, AT32): C++ namespace/static, this и signature, Pointer/Reference, невиртуальная база, отказы без исполнения (A4); квоты журнала с усечением, длинная серия 100 остановок, FAIL после усечения, живое окно (A1–A3); программная подмена входа в SRAM и через ret с потреблением прошивкой на CPU и отрицательным контролем (A5). 6×8 = 48/48 ожидаемых исходов, аудит 6×28 = 168/168, восстановление VERIFIED |
| H6 | PASS | Интерактивный режим (A7.5) на F411CE и F103C8: пауза 320 с, async с паузой дольше `timeout_s`, отмена, автоматический контроль; в интерфейсе VS Code — подтверждение владельца |
| F1 | PASS (AT32 — NOT_APPLICABLE) | tests/firmware/run_hw.py, локальный OpenOCD: F411CE, F401CC, F429ZI, F103, F030R8 — по 10/10 этапов; пакет (pack) на F411 — 10/10. AT32: J-Link с драйвером WinUSB не работает с SEGGER GDB Server, его маршрут в run_hw не предусмотрен |
| C1 | PASS | BluePill F103C8/F103CB: сборка и host 31/31 на каждом — Windows и Linux |
| C2 | PASS | BlackPill F411CE/F401CC: сборка и host 25/25 на каждом — Windows и Linux |
| C3 | PASS | Потребители на платах с модулем на кандидате: F411CE 22/22, F401CC 22/22, F103CB 28/28 (всего 72/72 PASS, по 44/44/56 записей) |
| R1 | PLANNED | Удалённый стенд по SSH: владелец переключит стенды на узел стенда, повтор run_hw и пакета |
| R2 | PLANNED | CI выпускного SHA — владелец |

Восстановление стендов: до кампании сняты полные копии Flash шести плат (AT32 — обе половины
по 512 КиБ), после кампании записаны обратно, повторно прочитаны и сверены по SHA-256 —
все шесть совпали; ядра работают. Mass erase и option bytes не использовались.

## Ограничения выпуска

- Эффект воздействий на кремнии подтверждён для программных входов (SRAM и ret) с потреблением
  прошивкой; физический сигнал, периферия и модель GPIO (A5.2) — только Renode.
- Привязка снимка GDB ко времени записи ROS (A6) по-прежнему не подтверждена (нет опоры после
  чтения); импорт и анализ — офлайн.
- Точка останова внутри `call` — только Renode; удалённый J-Link и AT32 в run_hw не проверялись.
- Интерактивный режим проверен на локальных стендах OpenOCD (ST-Link) в Windows; remote, Linux,
  J-Link и ST-LINK GDB Server — нет.
- ST-LINK GDB Server, SEGGER GDB Server и st-util сохраняют прежнюю приёмку.
- У сценариев BluePill чтение `$xPSR` через xPack OpenOCD (имя регистра `xpsr`) даёт ERROR;
  на локальном OpenOCD 0.12.0 — PASS. Исправление — в сценариях потребителя.
- Справочник API на Pages описывает изменения 0.5.0; карточки для вызовов C++, квот журнала
  и интерактивного режима — следующий документальный пакет.

## Свидетельства

Сводки лежат локально (не в Git): задания моста 367–389, `build/a8-hw/` (копии Flash и сверка),
комплекты `tests/sandbox/04-release-042/p3-hardware/pilot-060`, `tests/sandbox/08-release-060`
(H5), `build/live-observer-hw/a8-01`, `tests/hal-f030/build/validation/20261028T180305.655611Z`,
`build/hw/<профиль>-<профиль>-openocd/`, `build/a74-consumers/out/*-a8`. Компактный обзор и
технический отчёт кампании строятся навыком stm32-gdbtest-report из этих сводок.
