# Документация stm32-gdbtest

Документация · [English](../en/index.md)

Введение и назначение модуля — [README](../../README.md). Требования — [ТЗ](../TECHNICAL_SPECIFICATION.md)
(ведётся только на русском).

## Начало работы

- [Начало работы](GETTING_STARTED.md) — требования, проверка без платы, подключение подмодулем.
- [Написание тестов](TEST_AUTHORING.md) — процесс для человека и ИИ-агента.
- [API, CLI и миграция](API.md) — CMake, декоратор `case`, Target API, `run`, переход с hwtest.

## Механизмы

- [ELF/HAL-контракты](CONTRACTS.md) — offline-проверка функций, типов, enum и хэшей исходников.
- [HAL-макросы](HAL_MACRO_GUIDE.md) — выбор макросов, контекст и контракт макросов.
- [Образы и CRC](IMAGES.md) — секции ELF, BIN, полный образ и CRC-32/ISO-HDLC.
- [Manifest](MANIFESTS.md) — метаданные среды выполнения и происхождения сборки.
- [GDB-серверы](BACKENDS.md) — OpenOCD, ST-LINK GDB Server, J-Link; стенд.
- [Identity и Flash](TARGET_IDENTITY.md) — DEV_ID и заводской размер Flash.
- [Владение отладчиком](DEBUGGER_OWNERSHIP.md) — межпроектная блокировка на Windows и Linux.
- [Linux-стенд](LINUX_STAND.md) — окружение без root (Ubuntu 20.04, Orange Pi 5), USB, J-Link, WSL2.

## Состояние и сопровождение

- [Текущее состояние](STATUS.md) — проверенный объём, стенды и ограничения.
- [Проверки и CI](testing.md) — уровни CI, Docker-образ, аппаратная проверка CI-прошивок.
- [Версии и релизы](VERSIONING.md) — SemVer, теги, подготовка релиза.
- [Сопровождение](maintenance.md) — порядок работы, ветки, коммиты, двуязычная документация.
- [CHANGELOG](../../CHANGELOG.md), [дорожная карта](../../TODO.md), [AGENTS.md](../../AGENTS.md).
