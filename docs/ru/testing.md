# Проверки и CI

[Документация](index.md) → Проверки и CI · [English](../en/testing.md)

CI проверяет модуль до GDB-сервера: без отладчика, платы и доступа к MCU.
Аппаратные сценарии выполняются отдельно на согласованном стенде
([сопровождение](maintenance.md#работа-с-оборудованием)). Требования к CI —
п. 8.11–8.20 [ТЗ](../TECHNICAL_SPECIFICATION.md).

## Уровни проверок

| Уровень | Что проверяется | Где |
| --- | --- | --- |
| docs | `check_spec.py --strict` для ТЗ, локальные ссылки Markdown, пары RU/EN | `ci/run_checks.py docs`, workflow Docs |
| format | Исходники C/C++ соответствуют `.clang-format` (`clang-format --dry-run --Werror`, версия ≥ 16) | `ci/run_checks.py format` в Docker-образе, workflow Offline |
| host | Host-тесты модуля `Tests/host` | Linux в Docker-образе, Windows (Python 3.11, 3.13) и Ubuntu 20.04 x86_64/aarch64 на Python окружения стенда, workflow Offline |
| stand | Установка окружения Linux-стенда в чистом `ubuntu:20.04`, `doctor`, шаги `build` и `prepare` сценария `run_hw.py` для трёх профилей | Задание `linux-stand` workflow Offline на `ubuntu-24.04` и `ubuntu-24.04-arm` |
| firmware | Сборка CI-прошивок F030R8, F103C8, F411CE каждым GCC из lock-файла; build manifest; CTest `host` (traceability, `prepare.<ID>` с offline-контрактами); подготовка полного образа; отказ слишком малой политики образа; 10 отрицательных вариантов ELF-контрактов; наличие и выравнивание на 4 байта секций загрузки, включая `.data` | `ci/run_checks.py firmware` в Docker-образе, workflow Offline |

CI-прошивки находятся в [Tests/firmware](../../Tests/firmware/README.md): CMSIS без HAL и
без stm32-cmake-yml, по профилю на Cortex-M0, M3 и M4. Сценарии проверяют состояние
регистров и не являются доказательством поведения HAL. Аппаратный прогон
28.09.2026 — в [текущем состоянии](STATUS.md#аппаратная-проверка-ci-прошивок-2026-09-28).

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
  уровни host и firmware в Docker-образе на `ubuntu-24.04` без сети (`--network none`);
  задание `linux-stand` — окружение стенда в контейнере `ubuntu:20.04` (закреплён по digest) на x86_64 и
  aarch64 (сеть нужна для загрузки закреплённых архивов).
- **Hardware** — только вручную: сборка и `pack` на `ubuntu-24.04`, затем запуск пакетов
  на self-hosted раннере со стендом ([аппаратный CI](HARDWARE_CI.md)).

Фильтра по префиксу веток нет: ветки новых агентов проверяются без правки workflow.
Результат проверки относится к конкретному коммиту; сверяйте его с последним
коммитом ветки перед слиянием.

## Аппаратная проверка CI-прошивок (разработка)

Отдельно от CI те же прошивки проверяются на локальном стенде Windows или Linux
сценарием `Tests/firmware/run_hw.py`. Он собирает профиль, запускает сценарии через штатный
runner и GDB-сервер и сверяет ожидаемый исход каждого шага: запись и повтор без
записи, strict identity, полный образ с хвостом 0xA5, ожидаемый ERROR в verify-only,
восстановление 0xFF, timeout с восстановлением и повторный PASS.

```powershell
python -B Tests/firmware/run_hw.py --profile f411ce --stand Tests/firmware/stands/f411ce-openocd.local.toml
```

Стенд — локальная копия шаблона из `Tests/firmware/stands/*.example.toml`
(`*.local.toml` не коммитится). Toolchain и Cube — `--toolchain`, `--cube` или
`ARM_TOOLCHAIN_ROOT`, `STM32CUBE_REPOSITORY`; на Linux их задаёт `env.sh` окружения
стенда ([Linux-стенд](LINUX_STAND.md)), на Windows есть значения по умолчанию в
профиле пользователя. `summary.json` содержит ОС и архитектуру хоста. Итог — `build/hw/<профиль>-<стенд>/summary.json`.
Сценарий перезаписывает Flash: используйте только платы, согласованные для опытов.

## Чего CI не проверяет

- Подключение к GDB-серверу, отладчику и MCU, запись Flash, identity, Target API
  в работе, timeout/recovery — это аппаратные проверки потребителя.
- Блокировку отладчика между процессами — только host-тестами Windows и Linux.
- Удалённый GDB-сервер через настоящий SSH: host-тесты проверяют параметры SSH и
  вспомогательный скрипт без SSH; сквозной запуск через SSH проверяется вручную на
  стенде ([Linux-стенд](LINUX_STAND.md)).
- Семантику HAL и корректность сценариев на плате: контракты проверяют наличие
  символов, типов и раскрытие макросов в ELF.
