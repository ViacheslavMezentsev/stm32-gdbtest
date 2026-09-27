# Текущее состояние stm32-gdbtest

Срез: 2026-09-24. Runtime **0.1.0.dev0**, `API_VERSION = 1`; релизных тегов пока нет.
Основной способ поставки — закреплённый Git-подмодуль. Pip-пакет и console executable
пока не предоставляются. Этот документ описывает проверенный объём, а не журнал
каждого изменения; для истории служит [CHANGELOG](../CHANGELOG.md).

## Проверки

| Область | Доказанный объём |
| --- | --- |
| Host-инфраструктура | 71 unittest без MCU (на Linux 5 тестов блокировки Windows пропускаются) |
| CI (GitHub Actions, Docker) | Сборка CI-прошивок F030R8/F103C8/F411CE на GCC 13.3.1, 14.2.1, 15.2.1 с CMake 3.28.3, build manifest, `prepare`, offline-контракты с 10 отрицательными вариантами; host-тесты на Windows и Linux ([проверки и CI](ru/testing.md)) |
| ELF/HAL preflight | Положительный случай и 11 отрицательных вариантов на ELF F103C8/F401CC/F411CE |
| F411CE / ST-Link / OpenOCD | После отделения модуля 24/24 CTest в стендовом проекте: 22 HW + 2 host |
| F103C8 / J-Link | После отделения модуля 24/24 CTest: 22 HW + 2 host |
| Независимый consumer F411 | Build/offline, аппаратный сценарий, verify-only, timeout/recovery и восстановление основной прошивки; перенос/read-only dependency |
| F401CC / ST-Link и ST GDB Server на F1/F4 | Более ранние аппаратные проверки; не повтор всех новых macro-сценариев после отделения |

Число CTest-проверок относится к приложению потребителя, не к универсальному набору
модуля и не к проценту покрытия кода. Документальные изменения после интеграции
не считаются новыми аппаратными прогонами. Протоколы, ELF-хеши и ограничения:
[состояние стенда](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/STATUS.md),
[проверка consumer](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/CONSUMER_VALIDATION.md),
[методы и опыты](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/STM32_TESTING_METHODS.md).

Проверенные инструменты: xPack ARM GCC 13.3.1-1.1, GDB 14.2.90 со встроенным
Python 3.11.4, OpenOCD 0.12.0, ST server 7.14.0 из CubeCLT 1.22.0, J-Link 8.32.
F4 использует CubeF4 1.28.3, F1 — CubeF1 1.8.7. Номер GCC не гарантирует
состав GDB Python API, совпадение версии HAL не доказывает совпадение поведения.

## Ограничения реализации

- Аппаратный запуск — Windows; сборка, manifest и подготовка — также Linux. Ninja,
  один firmware target и один MCU/отладчик на запуск.
- Build manifest использует Cube/CMSIS metadata; универсальная сборочная система
  и поддержка произвольного toolchain не заявлены.
- J-Link device mapping проверен для STM32F103C8T6 → STM32F103C8 и STM32F030R8T6 → STM32F030R8.
- Target schema пока содержит обязательные OpenOCD-поля. H503 не поддержан проверками.
- -g3 нужен для macro debug info, но не сохраняет неиспользуемые функции.
  Контракты проверяют выбранные символы/типы/раскрытия, не всю семантику HAL.
- Halt меняет поведение MCU; измерение тока, точного времени и физических сигналов
  требует внешних методов. Одних регистровых проверок для этого недостаточно.
- Межпроектный mutex действует в одной Windows-сессии для участвующих runners.
  Vendor tools им не управляются; освобождение mutex после crash не гарантирует
  завершения дочернего сервера.
- Результаты PASS/FAIL/ERROR; автоматический SKIP, multi-node и управление питанием
  с reconnect пока не реализованы. Recovery — попытка восстановления, не гарантия
  при физическом отключении связи/питания.

Consumer содержит собственную прошивку. Его обычный CTest включает аппаратный тест
и может заменить Flash; `ctest --preset offline` аппаратного подключения не выполняет.

## Следующие этапы

Первый release candidate, надзор за серверными процессами, развитие профиля и
manifest; позднее — host-контроллер внешнего оборудования и Python-упаковка.
Это планы, не доступные сейчас возможности. [Полный TODO](../TODO.md),
[правила версий](VERSIONING.md), [начало работы](GETTING_STARTED.md).

## Регрессия ELF load sections, 2026-09-24

Host: 53/53, включая девять новых проверок gaps/LMA/границ/ошибок чтения
и отказ до сервера. В стендовом проекте: F411CE/ST-Link/OpenOCD 22/22 аппаратных
сценария, F103C8/J-Link 22/22; прошивки оставлены reset/run. Это проверка на
штатных STM32 ELF без промежутков; случай незагруженного gap проверен host-fixture
и offline разбором сохранённого K1921 ELF, без подключения разобранного стенда.
Политика [IMAGES](IMAGES.md); полный образ/CRC пока только запланирован.

## Полный образ / CRC, 2026-09-25

Host65/65. На F411CE/ST-Link/OpenOCD и F103C8/J-Link проверены полные 16 KiB:
программирование хвоста A5, повтор без записи, ожидаемый ERROR verify-only
при политике FF, восстановление FF, HW_BOOT и HW_GPIO с HAL-макросами после
реального load контейнера. CRC считается на ПК по readback, не блоком CRC MCU.
Полные прежние 22-сценарные наборы в этом этапе не повторялись; они проверены
на предыдущем этапе секций. ST server/RISC-V полный режим не проверены.
Подробности — [IMAGES](IMAGES.md), протокол FULL_IMAGE_CRC.md у потребителя.


F030R8/Cortex-M0: J-Link mapping STM32F030R8, J-Link GDB Server V8.32,
встроенный J-Link STLink, SWD. В стендовом проекте прошли 17 сценариев,
Flash/readback/reset-run; host65. Используется существующая схема профиля с
HardFault и доступными M0 диагностическими регистрами, без CFSR/HFSR.
Это не проверка всех Cortex-M0 или F0 backend-комбинаций.
[Протокол потребителя](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/F030_JLINK_VALIDATION.md).

## Аппаратная проверка CI-прошивок, 2026-09-28

Коммит `fbc103d`, `Tests/firmware/run_hw.py`, xPack GCC 13.3.1-1.1, GDB 14.2.90
(Python 3.11.4), CMSIS из STM32CubeF0 1.11.6, F1 1.8.7, F4 1.28.3. На каждом стенде
прошли все 10 шагов: сборка и CTest host, подготовка со стендом, запись и повтор без
записи, strict identity, полный образ 16 KiB с хвостом 0xA5, ожидаемый ERROR
verify-only без записи, восстановление 0xFF, timeout 0,2 с с восстановлением через
отдельный GDB-клиент и повторный PASS.

| Плата / MCU | Отладчик / backend | Результат |
| --- | --- | --- |
| NUCLEO-F030R8 / STM32F030R8 | J-Link STLink (V21), J-Link GDB Server 8.32 | 10/10 |
| WeAct BluePill-Plus / STM32F103C8 | J-Link CE (V9), J-Link GDB Server 8.32 | 10/10; предупреждение: заводской размер Flash 128 KiB при профиле 64 KiB |
| WeAct BlackPill / STM32F411CE | ST-Link V2J43M28, OpenOCD 0.12.0 | 10/10 |
| WeAct BlackPill / STM32F411CE | ST-Link V2J43M28, ST-LINK GDB Server 7.14.0 | 10/10, включая полный режим через ST server |

Первый прогон F030R8 выявил HardFault в `Reset_Handler`: адрес загрузки `.data` был
невыровнен, а Cortex-M0 не допускает невыровненного чтения слова. Скрипты
компоновщика CI-прошивок и минимального примера исправлены, CI проверяет
выравнивание секций загрузки. Это пример ошибки выполнения, которую не видят
проверки без оборудования. Стендовый набор stm32-hwtest-blackpill на этом коммите
не повторялся.
