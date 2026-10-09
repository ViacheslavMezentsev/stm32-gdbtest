# Текущее состояние stm32-gdbtest

[Документация](index.md) → Текущее состояние · [English](../en/STATUS.md)

**Сейчас (09.10.2026).** В ветке выпуска готовится кандидат v0.4.0: Python 0.4.0,
API_VERSION=2, ТЗ API 0.3.12, общее ТЗ 0.77. Состав в main до ветки — `f57fe72`;
[граница выпуска](RELEASE040_SCOPE.md) согласована. Итоговая аппаратная матрица и
потребитель с настоящим подмодулем ещё не проверены; выпуск не опубликован.
Опубликованный v0.3.0 принят на пяти платах по шести схемам:
[результаты](API_ACCEPTANCE.md), [метрики](HARDWARE_METRICS.md),
[описание выпуска](../releases/v0.3.0.md). Открытые пункты — [TODO](../../TODO.md).

Ниже — история предыдущих этапов; [подготовка v0.2.0-rc.1](RC020_READINESS.md) сохраняется для справки.

[F429 RTC/Sleep/deadline/recovery:20/20 HW +5 повторов, внешний timeout/recovery и HAL restore PASS; ТЗ0.57.](F429_CMSIS_RTC_SLEEP.md)

[F429 ADC/DMA/units/failures:15/15 HW +3 повтора, HAL восстановлена; ТЗ0.56.](F429_CMSIS_ADC_DMA.md)

[F429 CMSIS baseline:7/7 HW, HAL восстановлена; ТЗ0.55. Пятый профиль в CI, ADC/RTC ещё впереди.](F429_CMSIS_BASELINE.md)

[F401 RTC/Sleep/deadline/recovery:20/20 HW +5 повторов, внешний timeout/recovery и HAL restore PASS; ТЗ0.54.](F401_CMSIS_RTC_SLEEP.md)

[F401 ADC/DMA/units/failures:15/15 HW и три положительных повтора, HAL восстановлен; ТЗ0.53.](F401_CMSIS_ADC_DMA.md)

[F401 CMSIS baseline: 7/7 HW через ST-Link/OpenOCD, HAL boot/blink восстановлены. Flash256/RAM64; ADC/RTC ещё не перенесены.](F401_CMSIS_BASELINE.md)

Срез rc.2: 5b7b466. Docs/Offline/Hardware SUCCESS; все 27 JSON из GitHub проверены.
Windows: F030 CMSIS 18/18, HAL 17/17 с повторами/recovery; циклы F030/OpenOCD,
F103/J-Link, F411/OpenOCD — по 10/10. ST server завершён после USB reconnect;
это не непрерывный 10/10, причина USB-сбоя не установлена. Все исходные HAL
восстановлены. [Подробный протокол и оставшиеся условия](RC2_READINESS.md).

Опубликован rc.2 на a0d6547. После тега приняты группы F103 baseline (352417c)
и ADC/DMA (3e123ad). Новая [RTC/Sleep](F103_CMSIS_RTC_SLEEP.md):
20/20 HW, пять положительных повторов, timeout/recovery и HAL restore PASS.
Первоначальные ошибки ACL при восстановлении сохранены в протоколе.

## Текущий состав и доказательства

| Область | Проверенный объём и границы |
| --- | --- |
| Host | 98 unittest; Windows: 8 платформенных skips. Linux пропускает Windows-only проверки; точный результат сохраняется в журнале, пропуски не считаются HW PASS |
| Offline CI | Docs, format, host; CMSIS F030/F103/F411 × GCC13/14/15; отдельный HAL F030 на GCC13, 19 CTest и 5 отрицательных contracts. Все пять jobs Offline прошли на 5b7b466 |
| CMSIS F030 | 18 сценариев: boot/clock/GPIO/blink, TIM3, ADC/DMA/численные векторы, Sleep, RTC и отказы. HW: единый прогон 18/18 на 5b7b466 локально Windows; HAL восстановлен. Ранее SSH/Orange Pi на a48158c; см. RC2_READINESS |
| HAL F030 | Автономный tests/hal-f030: 17/17, шесть повторов после инъекций, ожидаемый timeout ERROR, recovery и восстановление HAL потребителя — Windows/ST-Link/OpenOCD |
| CMSIS F103/F411 | После rc.2: F103 20/20 HW clocks/GPIO/SysTick/TIM2/ADC/DMA/RTC/Sleep + 5 normal repeats, timeout/recovery; F411 — 20/20 HW baseline/ADC/DMA/RTC/Sleep +5 повторов, timeout/recovery, HAL восстановлен. Полный перенос периферии не завершён |
| minimal-consumer F411 | Отдельный пример подключения CMake без YAML; проверяет подключение модуля, не полную периферию платы |
| Потребитель BlackPill | fb2d186 / модуль 67b7431: Offline SUCCESS, пять профилей/120 CTest; Windows 25/25, F411/OpenOCD 22/22 + timeout/recovery/restore. Итоговый gitlink обновляется после land модуля |

Источники: [HAL→CMSIS](F030_CMSIS_ACCEPTANCE.md), [HAL-протокол](F030_HAL_VALIDATION.md),
[техники](TESTING_TECHNIQUES.md), [CI](testing.md).
Текущий Nucleo-стенд — родной ST-Link/OpenOCD; результаты J-Link STLink ниже исторические.
F103 — WeAct BluePill-Plus/J-Link; F411 — BlackPill/ST-Link с OpenOCD и ST server.
Удалённые запуски, пакеты и Hardware workflow повторены при приёмке rc.2;
точные SHA и границы — RC2_READINESS. Отдельный Linux-ПК с USB и WSL usbipd остаются
непроверенными конфигурациями. Число сценариев не является процентом покрытия.

## Схемы размещения стенда

Локальные Windows и Orange Pi 5/Linux, Windows/WSL → сервер по SSH,
pack/run --package и Hardware workflow реализованы и проверялись для rc.1.
Это историческая матрица ниже, не итоговая приёмка rc.2.
Приёмка rc.2 завершена по [матрице выпуска](RC2_READINESS.md).

## Итоговая проверка 0.1.0-rc.1, 2026-09-29

Историческая проверка rc.1: коммит `2143665` (версия `0.1.0rc1`).
Результаты этого раздела не распространяются автоматически на изменения после rc.1.

| Проверка | Результат |
| --- | --- |
| CI: Docs, Offline (format, host Windows/Linux, CI-прошивки на GCC 13/14/15, окружение Linux-стенда) | зелёный |
| `run_hw.py` на Windows: F030R8 / J-Link STLink, F103C8 / J-Link CE, F411CE / OpenOCD, F411CE / ST-LINK GDB Server | 4 × 10/10 |
| `run_hw.py` с Windows, GDB-серверы на Orange Pi 5 по SSH: F030R8 / J-Link, F103C8 / J-Link, F411CE / OpenOCD | 3 × 10/10 |
| Workflow Hardware: пакеты собраны на GitHub, запуск на раннере-службе Orange Pi 5 | 3 × 10/10 |
| Проект потребителя STM32G474, runner на Windows, OpenOCD на Orange Pi 5: CTest host 5/5, сценарии на плате | 4/4 PASS |

На NUCLEO-F030R8 J-Link STLink на Windows показывает окно условий использования;
его нужно подтвердить до прогона, иначе подключение ждёт ответа.

## Аппаратная проверка CI-прошивок, 2026-09-28

Коммит `fbc103d`, `tests/firmware/run_hw.py`, xPack GCC 13.3.1-1.1. На каждом стенде
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
компоновщика исправлены, CI проверяет выравнивание — это пример ошибки выполнения,
которую не видят проверки без оборудования. После `fbc103d` изменено формирование
BIN (только выбранные секции); перед выпуском аппаратная проверка повторена на
итоговом коммите (п. 8.19 [ТЗ](../TECHNICAL_SPECIFICATION.md), раздел выше). Стендовый набор
stm32-hwtest-blackpill на этих коммитах не повторялся.

## Ограничения реализации

- Аппаратный запуск — Windows и Linux x86_64/aarch64 (glibc ≥ 2.31); на Linux он
  проверен на Orange Pi 5 (aarch64) с OpenOCD, J-Link CE и J-Link STLink; Linux x86_64 — только как
  компьютер запуска в WSL2 с сервером на Orange Pi, с локальным отладчиком не проверялся. GDB-сервер работает на компьютере
  runner или на хосте стенда Linux по SSH (`[remote]`); удалённый режим проверен с Windows
  и из WSL2 на Orange Pi 5; обрыв связи проверен выдёргиванием кабеля Orange Pi: сервер остановлен сигналом присутствия через 13 с. Ninja, один firmware target и один MCU и отладчик на запуск.
- ST-LINK GDB Server на Linux aarch64 недоступен (сервер ST не выпускается для arm64).
- Build manifest использует метаданные Cube и CMSIS; универсальная система сборки
  и произвольный toolchain не заявлены.
- J-Link mapping проверен для STM32F103C8T6 → STM32F103C8, STM32F030R8T6 → STM32F030R8 и
  STM32F103CBT6 → STM32F103CB (WeAct BluePill-Plus, демонстрационный проект stm32-hwtest-bluepill).
- Target schema содержит обязательные поля OpenOCD. H503 не поддержан.
- `-g3` нужен для макросов в отладочной информации, но не сохраняет неиспользуемые
  функции. Контракты проверяют выбранные символы, типы и раскрытия, а не всю
  семантику HAL.
- Halt меняет поведение MCU; ток, точное время и физические сигналы требуют внешних
  методов.
- Межпроектная блокировка действует в одной Windows-сессии или на одном хосте Linux
  для участвующих runner; vendor tools ею не управляются, освобождение после аварии
  не гарантирует завершения дочернего сервера. Блокировки Windows и WSL независимы.
- Результаты — PASS, FAIL, ERROR; автоматического SKIP, multi-node и управления
  питанием с reconnect нет. Recovery — попытка восстановления, не гарантия при
  физическом отключении связи или питания.

Пример потребителя содержит собственную прошивку: его полный CTest включает
аппаратный тест и может заменить Flash, а `ctest --preset offline` к плате не
подключается.

## Следующие этапы

Подготовка [rc.2](RC2_READINESS.md), затем продолжение CMSIS-миграции и работа
по [TODO](../../TODO.md). RISC-V, внешнее управление стендом и Python-упаковка
остаются планами.


## Предыдущая сводка проверок (до аудита rc.2)

| Область | Доказанный объём |
| --- | --- |
| CI (GitHub Actions, Docker) | Docs, format, host на Windows и Linux; CI-прошивки F030R8/F103C8/F411CE на GCC 13.3.1, 14.2.1, 15.2.1 с CMake 3.28.3: build manifest, `prepare`, полный образ, 10 отрицательных контрактов, выравнивание секций загрузки, пустая секция в RAM; окружение Linux-стенда в `ubuntu:20.04` на x86_64 и aarch64 ([проверки и CI](testing.md)) |
| CI-прошивки на оборудовании | Итоговая проверка на `2143665`: 4 стенда на Windows, 3 стенда с Windows на Orange Pi 5, 3 стенда в workflow Hardware — по 10/10 шагов; ранее 4 стенда на `fbc103d` (разделы ниже) |
| Linux-стенд без оборудования | Ubuntu 20.04 x86_64 (glibc 2.31, Python 3.8, git 2.25) в контейнере: установка окружения, host-тесты (79 на ревизии 0.7), `doctor`, `build` и `prepare` CI-прошивок; аппаратный путь без отладчика — блокировка, запуск OpenOCD, ERROR «exited before ready», процессы остановлены |
| Удалённый GDB-сервер на оборудовании | Runner и GDB на Windows 10, GDB-серверы на Orange Pi 5 по SSH: F411CE / OpenOCD, F103C8 / J-Link CE, F030R8 / J-Link STLink — по 10/10 (`run_hw.py`) |
| Удалённый GDB-сервер без оборудования | Петля SSH (OpenSSH, ключ, `known_hosts`) и фиктивный J-Link сервер: проброс порта, подключение GDB через туннель, recovery, остановка сервера и передача журнала, отказ при занятой блокировке хоста стенда, очистка после обрыва сессии |
| Linux-стенд на оборудовании | Orange Pi 5, Ubuntu 20.04 aarch64, `run_hw.py`: F411CE / ST-Link V2J43M28 / xPack OpenOCD 0.12.0-7 — 10/10; F103C8 / J-Link CE V9 / J-Link GDB Server 8.32 arm64 — 10/10; F030R8 / J-Link STLink V21 / J-Link GDB Server 9.80 arm64 — 10/10 после подтверждения окна условий J-Link STLink в графическом сеансе; без этого подключение ждёт около 10 с, первый прогон — 2/10 ([Linux-стенд](LINUX_STAND.md)) |
| ELF/HAL preflight | Положительный случай и 11 отрицательных вариантов на ELF F103C8/F401CC/F411CE стендового проекта |
| Стендовый проект, F411CE / ST-Link / OpenOCD | 24/24 CTest (22 HW + 2 host) после отделения модуля |
| Стендовый проект, F103C8 / J-Link | 24/24 CTest (22 HW + 2 host) |
| Стендовый проект, F030R8 / J-Link STLink | 17/17 HW |
| Стендовый проект, F429ZI / ST-Link/V2 | 22/22 HW через OpenOCD и ST server на модуле `b76d909`; единичные сбои USB в длинных сериях ([протокол](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/F429_SERVER_STABILITY.md)) |
| Независимый consumer F411 | Сборка и offline, аппаратный сценарий, verify-only, timeout/recovery и восстановление основной прошивки |
| Проект потребителя, STM32G474 / ST-Link через Orange Pi 5 | Arduino Core STM32 (HAL и CMSIS не из STM32Cube), stm32-cmake-yml с CRC в ELF после линковки, C++ с LTO, xPack GCC 14.2.1 (GDB 15.2.90, Python 3.12.8); runner на Windows, OpenOCD на Orange Pi по SSH. Четыре сценария PASS на одной сборке без LTO: загрузка (DEV_ID `0x469`, заморозка IWDG при остановке), завершение `setup()`, 15 вызовов `setup()` по порядку, инъекция отказа питания через `force_return` — первая аппаратная проверка `force_return`. Подключение выявило отказ manifest без пакетов STM32Cube (исправлен, ТЗ 0.16) |
| F401CC / ST-Link, ST server на F1/F4 | Более ранние аппаратные проверки; новые macro-сценарии после отделения модуля не повторялись |

Число сценариев относится к приложению потребителя, а не к универсальному набору
модуля и не к проценту покрытия. Изменения документации не считаются новыми
аппаратными прогонами. Протоколы, хэши ELF и ограничения стендового проекта:
[состояние стенда](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/STATUS.md),
[проверка consumer](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/CONSUMER_VALIDATION.md),
[методы и опыты](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/STM32_TESTING_METHODS.md).

Проверенные инструменты: xPack ARM GCC 13.3.1-1.1, GDB 14.2.90 со встроенным
Python 3.11.4, OpenOCD 0.12.0, ST-LINK GDB Server 7.14.0 (CubeCLT 1.22.0), J-Link 8.32;
CubeF0 1.11.6, CubeF1 1.8.7, CubeF4 1.28.3. В CI дополнительно собираются GCC 14.2.1 и
15.2.1 (GDB 15.2.90 и 16.3.90 с Python 3.12 и 3.13). Номер GCC не гарантирует состав
GDB Python API; совпадение версии HAL не доказывает совпадения поведения.

## История проверок

**Регрессия ELF load sections, 2026-09-24.** Host 53/53, включая девять проверок
промежутков, LMA, границ и ошибок чтения с отказом до сервера. Стендовый проект:
F411CE/ST-Link/OpenOCD 22/22, F103C8/J-Link 22/22; прошивки оставлены в reset/run.
Случай незагруженного промежутка проверен host-fixture и offline-разбором
сохранённого ELF К1921 без подключения стенда. Политика — [образы и CRC](IMAGES.md).

**Полный образ и CRC, 2026-09-25.** Host 65/65. На F411CE/ST-Link/OpenOCD и
F103C8/J-Link проверены полные 16 KiB: запись хвоста 0xA5, повтор без записи,
ожидаемый ERROR verify-only при политике 0xFF, восстановление 0xFF, HW_BOOT и HW_GPIO
с HAL-макросами после реального load контейнера. CRC считается на ПК по readback.
Полные 22-сценарные наборы на этом этапе не повторялись. Протокол — FULL_IMAGE_CRC.md
стендового проекта.

**F030R8 / Cortex-M0, 2026-09-25.** J-Link mapping `STM32F030R8`, J-Link GDB Server
8.32, встроенный J-Link STLink, SWD. В стендовом проекте прошли 17 сценариев,
запись, чтение и reset/run; host 65. Схема профиля прежняя: HardFault и доступные
на M0 диагностические регистры без CFSR/HFSR. Это не проверка всех Cortex-M0 и
комбинаций backend для F0.
[Протокол потребителя](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/F030_JLINK_VALIDATION.md).

[F411 CMSIS baseline](F411_CMSIS_BASELINE.md): HSI16, PC13, SysTick, TIM2; post-rc.2.

[F411 ADC/DMA](F411_CMSIS_ADC_DMA.md): factory calibration, numerical vectors and state faults.

[F411 RTC/Sleep](F411_CMSIS_RTC_SLEEP.md): calendar Alarm A, WFI and recovery.

[Итоговая сверка пяти профилей и оставшиеся HAL-проверки](CMSIS_ACCEPTANCE.md).

[HAL F030: пять GPIO/RCC-техник и варианты исходников](F030_HAL_GPIO_RCC.md).
