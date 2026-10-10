# Профили MCU

[Документация](index.md) → Профили MCU · [English](../en/MCU_PROFILES.md)

Профиль — файл `target.toml` с описанием конкретного MCU: Flash, DEV_ID, число
hardware breakpoints, обработчики отказов, диагностические регистры, цель OpenOCD.
Готовой библиотеки профилей «для любого STM32» в модуле нет: профиль пишет
потребитель под свою плату, взяв за образец один из имеющихся. Несколько вариантов
MCU одной прошивки могут делить сценарии, каждый со своим `session.toml`, указывающим профиль через `config.target`.

Образцы в репозитории: CI-прошивки `tests/firmware/profiles/` (F030R8, F103C8, F401CC,
F411CE, F429ZI — Cortex-M0, M3, M4; AT32F403A — совместимый Cortex-M4) и пример
`examples/minimal-consumer/profile/` (F411CE).

| MCU | Отладчик / GDB-сервер | Где проверено |
| --- | --- | --- |
| STM32F030R8 | ST-Link (NUCLEO) / OpenOCD, st-util; J-Link GDB Server | CI-прошивка, HAL-фикстура, стендовый проект |
| STM32F103C8 | J-Link / J-Link GDB Server; ST-Link / st-util | CI-прошивка, стендовый проект |
| STM32F103CB | J-Link CE / J-Link GDB Server | демонстрационный проект [stm32-hwtest-bluepill](https://github.com/ViacheslavMezentsev/stm32-hwtest-bluepill) |
| STM32F401CC | ST-Link / OpenOCD; ST-LINK GDB Server; st-util | CI-прошивка, стендовый проект |
| STM32F411CE | ST-Link / OpenOCD; ST-LINK GDB Server; st-util | CI-прошивка, пример, стендовый проект |
| STM32F429ZI | ST-Link / OpenOCD; ST-LINK GDB Server; st-util | CI-прошивка, стендовый проект |
| STM32G474CE | ST-Link / OpenOCD на Orange Pi 5 | проект потребителя (Arduino Core STM32) |
| AT32F403ACGU7 (Artery) | J-Link / J-Link GDB Server; ST-Link / st-util | CI-прошивка, после 0.3.0 |

Для OpenOCD, ST-LINK GDB Server и st-util достаточно профиля. J-Link GDB Server требует
имени устройства: оно задаётся в профиле (`jlink_device`), а для STM32F103C8T6,
STM32F030R8T6 и STM32F103CBT6 известно модулю. H503 не поддержан. Поддержка определяется конкретной
комбинацией MCU, HAL, GDB и backend, а не семейством: [текущее состояние](STATUS.md).

**Совместимые МК других производителей.** Модуль не привязан к ST: нужны ядро Cortex-M и
GDB-сервер, который подключается к кристаллу. Такой МК (Artery AT32, GigaDevice GD32, Geehy APM32
и т. п.) подключается своим профилем и CMSIS производителя, без изменений модуля. Проверен пока один —
AT32F403ACGU7 на WeAct AT32F4 Core Board через J-Link; он не входит в аппаратную кампанию 0.3.0;
он учитывается в шести моделях 0.4.0. Профиль, SDK, особенности сценариев и порядок подключения своего МК —
в [совместимых МК](COMPATIBLE_MCU.md). Каждый новый кристалл требует своей приёмки на плате.

