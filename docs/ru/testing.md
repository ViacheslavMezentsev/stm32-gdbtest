# Проверки и CI

Документация → Проверки и CI · [English](../en/testing.md)

CI проверяет модуль до GDB-сервера: без отладчика, платы и доступа к MCU.
Аппаратные сценарии выполняются отдельно на согласованном стенде
([сопровождение](maintenance.md#работа-с-оборудованием)). Требования к CI —
п. 8.11–8.16 [ТЗ](../TECHNICAL_SPECIFICATION.md).

## Уровни проверок

| Уровень | Что проверяется | Где |
| --- | --- | --- |
| docs | `check_spec.py --strict` для ТЗ, локальные ссылки Markdown, пары RU/EN | `ci/run_checks.py docs`, workflow Docs |
| host | Host-тесты модуля `Tests/host` | Linux в Docker-образе и Windows (Python 3.11, 3.13), workflow Offline |
| firmware | Сборка CI-прошивок F030R8, F103C8, F411CE каждым GCC из lock-файла; build manifest; CTest `host` (traceability, `prepare.<ID>` с offline-контрактами); подготовка полного образа; отказ слишком малой политики образа; 10 отрицательных вариантов ELF-контрактов | `ci/run_checks.py firmware` в Docker-образе, workflow Offline |

CI-прошивки находятся в [Tests/firmware](../../Tests/firmware/README.md): CMSIS без HAL и
без stm32-cmake-yml, по профилю на Cortex-M0, M3 и M4. Их сценарии на оборудовании
не запускались и не являются доказательством поведения HAL.

Результаты — `build/ci/summary.json`; журналы — `Tests/firmware/build/<профиль>-gcc<версия>/ci.log`.
В GitHub они сохраняются артефактом `offline-results`.

## Окружение

Образ `ci/docker/Dockerfile` собирается из закреплённого [lock-файла](../../ci/dependencies.lock.json):
Ubuntu 24.04 по digest, xPack GCC 13.3.1-1.1, 14.2.1-1.1, 15.2.1-1.1 (каждый с
`arm-none-eabi-gdb-py3`), CMake 3.28.3, Ninja 1.12.1, CMSIS из STM32CubeF0 1.11.6,
F1 1.8.7 и F4 1.28.3 (только `Drivers/CMSIS`) и `check_spec.py` навыка
embedded-tech-spec. Версии GCC и CMake совпадают с stm32-cmake-yml; CMake 3.19.8
не используется, так как модулю нужен CMake ≥ 3.25. Архивы проверяются по SHA-256,
репозитории — по коммиту. При сборке образ проверяет GDB-Python каждого GCC.

## Запуск локально

Docker Desktop (Windows) или Docker Engine (Linux), из корня репозитория:

```powershell
docker build -f ci/docker/Dockerfile -t stm32-gdbtest-ci:local .
docker run --rm --network none --mount "type=bind,source=${PWD},target=/workspace" `
  stm32-gdbtest-ci:local python3 ci/run_checks.py
```

В Linux продолжение строки — `\`, а для файлов с правами текущего пользователя
добавьте `--user "$(id -u):$(id -g)" -e HOME=/tmp`. Выборочно:
`python3 ci/run_checks.py firmware --gcc 13.3.1-1.1 --profile f411ce`.
Без аргументов выполняются все уровни. Уровень docs использует `CHECK_SPEC` из образа.

Если реестр Docker Hub недоступен, передайте зеркало того же образа Ubuntu 24.04:
`--build-arg BASE_IMAGE=<зеркало>/ubuntu:24.04`. Значение по умолчанию закреплено digest.

Без Docker: host-тесты — `python -B -m unittest discover -s Tests/host -v`;
CI-прошивка — presets в `Tests/firmware` (`cmake --preset f411ce`,
`cmake --build --preset f411ce`, `ctest --preset f411ce-offline`) при заданных
`ARM_TOOLCHAIN_ROOT` и `STM32CUBE_REPOSITORY`.

## Workflows GitHub Actions

- **Docs** — при каждом push в любую ветку: уровень docs.
- **Offline** — при push в любую ветку, кроме изменений только Markdown, `LICENSE`
  и `.github/FUNDING.yml`: host-тесты на `windows-2022` (Python 3.11 и 3.13) и
  уровни host и firmware в Docker-образе на `ubuntu-24.04` без сети (`--network none`).

Фильтра по префиксу веток нет: ветки новых агентов проверяются без правки workflow.
Результат проверки относится к конкретному коммиту; сверяйте его с последним
коммитом ветки перед слиянием.

## Чего CI не проверяет

- Подключение к GDB-серверу, отладчику и MCU, запись Flash, identity, Target API
  в работе, timeout/recovery — это аппаратные проверки потребителя.
- Блокировку отладчика между процессами — только host-тестами Windows.
- Семантику HAL и корректность сценариев на плате: контракты проверяют наличие
  символов, типов и раскрытие макросов в ELF.
