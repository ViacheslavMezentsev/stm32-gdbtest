# Проверки и CI

[Документация](index.md) → Проверки и CI · [English](../en/testing.md)

[Практический порядок Docker и L6](local-ci.md): снимок, volume, отчёты и восстановление стенда.

## Уровни доказательств

Нормативная классификация — общее ТЗ 9.3. Это не порядок вызова команд CI.

| Уровень | Подтверждает | Не подтверждает | Средства |
| --- | --- | --- | --- |
| L0 | Окружение, версии и хеши зависимостей | Логику модуля | ci/docker/verify.py, doctor |
| L1 | Документы, ссылки, RU/EN и границы публикации | Смысл текста и работу кода | docs, docs.public |
| L2 | Host-логику с подменами | Реальный GDB/backend/MCU | tests/host |
| L3 | CMake Configure/Generate и регистрацию тестов | Сборку и исполнение | CMake host-тесты, потребитель |
| L4 | ELF/образы, секции и manifest | Исполнение firmware | GCC-матрица CMSIS/HAL |
| L5 | Offline GDB, DWARF, контракты и подготовку | MCU и периферию | prepare, contract_preflight |
| L6 | Исполнение и восстановление на конкретном стенде | Все платформы и полноту покрытия | run_hw.py, run_suite.py |

Группы команд ниже могут охватывать несколько уровней; format — отдельный контроль стиля.
QEMU/Renode не реализованы как уровень приёмки. L6 входит в выпускную приёмку модуля.
`docs.public` читает выделенные фильтры .gitignore, запрещает публикацию локальных
материалов и ссылки на них, независимо от существования файла у разработчика.


CI проверяет модуль до GDB-сервера: без отладчика, платы и доступа к MCU.
Аппаратные сценарии выполняются отдельно на согласованном стенде
([сопровождение](maintenance.md#работа-с-оборудованием)). Требования к CI —
п. 8.11–8.20 [ТЗ](../TECHNICAL_SPECIFICATION.md).

## Уровни проверок

| Уровень | Что проверяется | Где |
| --- | --- | --- |
| docs | `check_spec.py --strict` для ТЗ, локальные ссылки Markdown, пары RU/EN | `ci/run_checks.py docs`, workflow Docs |
| format | Исходники C/C++ соответствуют `.clang-format` (`clang-format --dry-run --Werror`, версия ≥ 16) | `ci/run_checks.py format` в Docker-образе, workflow Offline |
| host | Host-тесты модуля `tests/host` | Linux в Docker-образе, Windows (Python 3.11, 3.13) и Ubuntu 20.04 x86_64/aarch64 на Python окружения стенда, workflow Offline |
| stand | Установка окружения Linux-стенда в чистом `ubuntu:20.04`, `doctor`, шаги `build` и `prepare` сценария `run_hw.py` для трёх профилей | Задание `linux-stand` workflow Offline на `ubuntu-24.04` и `ubuntu-24.04-arm` |
| firmware | Сборка CI-прошивок F030R8, F103C8, F401CC, F411CE, F429ZI, AT32F403A каждым GCC из lock-файла; build manifest; CTest `host` (traceability, `prepare.<ID>` с offline-контрактами); подготовка полного образа; отказ слишком малой политики образа; 10 отрицательных вариантов ELF-контрактов; наличие и выравнивание на 4 байта секций загрузки, включая `.data` | `ci/run_checks.py firmware` в Docker-образе, workflow Offline |
| hal | HAL F030/GCC13: 24 CTest, 22 prepare JSON, положительный и 5 отрицательных contracts; без сервера | `ci/run_checks.py hal`, workflow Offline |

CI-прошивки находятся в [tests/firmware](../../tests/firmware/README.md): CMSIS без HAL и
без stm32-cmake-yml, по профилю на Cortex-M0, M3 и M4. Сценарии проверяют состояние
регистров и не являются доказательством поведения HAL. Аппаратный прогон
28.09.2026 — в [текущем состоянии](STATUS_ARCHIVE.md#аппаратная-проверка-ci-прошивок-2026-09-28).

Результаты — `build/ci/<run>/summary.json`; журналы — `tests/firmware/build/ci/<run>/<профиль>-gcc<версия>/ci.log`.
В GitHub они сохраняются артефактом `offline-results`.

## Workflows GitHub Actions

- **Docs** — при каждом push в любую ветку: уровень docs.
- **Offline** — при push в любую ветку, кроме изменений только Markdown, `LICENSE`
  и `.github/FUNDING.yml`: host-тесты на `windows-2022` (Python 3.11 и 3.13) и
  уровни format, host, firmware и hal в Docker-образе на `ubuntu-24.04` без сети (`--network none`);
  задание `linux-stand` — окружение стенда в контейнере `ubuntu:20.04` (закреплён по digest) на x86_64 и
  aarch64 (сеть нужна для загрузки закреплённых архивов).
- **Hardware** — только вручную: сборка и `pack` на `ubuntu-24.04`, затем запуск пакетов
  на self-hosted раннере со стендом ([аппаратный CI](HARDWARE_CI.md)).

Фильтра по префиксу веток нет: ветки новых агентов проверяются без правки workflow.
Результат проверки относится к конкретному коммиту; сверяйте его с последним
коммитом ветки перед слиянием.

## Чего CI не проверяет

- Подключение к GDB-серверу, отладчику и MCU, запись Flash, identity, Target API
  в работе, timeout/recovery — это аппаратные проверки потребителя.
- Блокировку отладчика между процессами — только host-тестами Windows и Linux.
- Удалённый GDB-сервер через настоящий SSH: host-тесты проверяют параметры SSH и
  вспомогательный скрипт без SSH; сквозной запуск через SSH проверяется вручную на
  стенде ([Linux-стенд](LINUX_STAND.md)).
- Семантику HAL и корректность сценариев на плате: контракты проверяют наличие
  символов, типов и раскрытие макросов в ELF.

## HAL F030 в offline CI

[Состав проверки и команды](local-ci.md#hal-f030-в-offline-ci).
