# Стенды

[Документация](index.md) → Стенды · [English](../en/STANDS.md)

Платы, на которых проверяется модуль: CI-прошивки `tests/firmware/profiles/`, HAL-фикстура F030,
пример live-observer и демонстрационные потребители
[stm32-hwtest-bluepill](https://github.com/ViacheslavMezentsev/stm32-hwtest-bluepill) и
[stm32-hwtest-blackpill](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill).
Профиль MCU описан в [профилях](MCU_PROFILES.md), отладчики — в [GDB-серверах](BACKENDS.md),
размещение процессов — в [схемах запуска](RUN_LAYOUTS.md), результаты — в [приёмке](API_ACCEPTANCE.md).

Рисунки — схематичный вид сверху в одном масштабе (1 мм = 6 пикселей), ориентация как на снимках стендов.
Показаны только детали, важные для стенда: MCU, разъёмы, кнопки, светодиоды, кварцы, гребёнки и SWD.
Положения приблизительные (около 0,5 мм); рисунки строит `docs/images/stands/make_stands.py`.

## Сводка

| Плата | MCU | Ядро, частота | Flash / SRAM | Кварцы HSE / LSE | Светодиод / кнопка | Отладчик на стенде |
| --- | --- | --- | --- | --- | --- | --- |
| ST NUCLEO-F030R8 (MB1136 rev C) | STM32F030R8T6, LQFP64 | Cortex-M0, 48 МГц | 64 / 8 KiB | 8 МГц от MCO ST-LINK / 32,768 кГц (X2) | LD2 PA5, активный высокий / B1 PC13 | встроенный ST-LINK/V2-1 |
| WeAct BluePill-Plus | STM32F103CBT6, LQFP48 | Cortex-M3, 72 МГц | 128 / 20 KiB | 8 МГц / 32,768 кГц | PB2, активный высокий / KEY PA0 | внешний ST-Link или J-Link по SWD |
| WeAct MiniF4, ранняя ревизия | STM32F401CCU6, QFN48 | Cortex-M4F, 84 МГц | 256 / 64 KiB | 25 МГц / 32,768 кГц | PC13 / UKEY PA0 | внешний ST-Link по SWD |
| WeAct BlackPill V2/V3 | STM32F411CEU6, QFN48 | Cortex-M4F, 100 МГц | 512 / 128 KiB | 25 МГц / 32,768 кГц | C13, активный низкий / KEY PA0 | внешний ST-Link по SWD |
| ST STM32F429I-DISCO (MB1075B) | STM32F429ZIT6, LQFP144 | Cortex-M4F, 180 МГц | 2048 / 256 KiB | 8 МГц от MCO ST-LINK / не установлен | LD3 PG13, LD4 PG14 / B1 PA0 | встроенный ST-LINK/V2 |
| WeAct AT32F403A V1.0 | Artery AT32F403ACGU7, QFN48 | Cortex-M4F, 240 МГц | 1024 / 96 KiB¹ | см. схему WeAct | C13, активный низкий / KEY | J-Link (WinUSB) по SWD |

¹ Flash — по профилю `tests/firmware/profiles/at32f403a`; SRAM — по описанию WeAct (96 KiB, ещё 128 KiB в
расширенном режиме кристалла, который модуль не использует).

Одна плата BluePill-Plus с STM32F103CBT6 обслуживает оба профиля stm32-hwtest-bluepill (F103C8 и F103CB).
CI-профиль `f103c8` модуля запускается на ней же. Ревизия MiniF4 с F401CC отличается от BlackPill V2/V3:
micro-USB, кнопка UKEY, светодиоды D2/D3 и четыре крепёжных отверстия.

Хосты: Windows (runner, GDB, OpenOCD, ST-LINK GDB Server, J-Link) и Linux-стенд Orange Pi 5
(Ubuntu 20.04) для схем с GDB-сервером по SSH ([Linux-стенд](LINUX_STAND.md)).

## Платы

### NUCLEO-F030R8

![NUCLEO-F030R8](../images/stands/nucleo-f030r8.svg)

Отладчик ST-LINK/V2-1 встроен (слева, отламываемая часть), USB Mini-B. Гребёнки morpho CN7/CN10 и
разъёмы Arduino Uno V3. Используется CI-прошивкой `f030r8` и HAL-фикстурой `tests/hal-f030`.
Источник: [UM1724](https://www.st.com/resource/en/user_manual/dm00105823.pdf).

### WeAct BluePill-Plus (STM32F103CBT6)

![WeAct BluePill-Plus](../images/stands/weact-bluepill-plus-f103cb.svg)

USB-C, кнопки NRST и BOOT0 слева, KEY справа, 4-контактный SWD на торце. Источник:
[WeActStudio/BluePill-Plus](https://github.com/WeActStudio/BluePill-Plus).

### WeAct MiniF4 (STM32F401CCU6), ранняя ревизия

![WeAct MiniF4 F401CC](../images/stands/weact-minif4-f401cc.svg)

micro-USB, кнопки UKEY, RST, BOOT0, светодиоды D2 и D3. Источник:
[WeActStudio.MiniSTM32F4x1](https://github.com/WeActStudio/WeActStudio.MiniSTM32F4x1).

### WeAct BlackPill V2/V3 (STM32F411CEU6)

![WeAct BlackPill F411CE](../images/stands/weact-blackpill-f411ce.svg)

USB-C, кнопки NRST, BOOT0 и KEY, светодиоды C13 и PWR, 4-контактный SWD. Используется CI-прошивкой
`f411ce`, примером live-observer (VTOR/FPB) и потребителем stm32-hwtest-blackpill. Источники:
[WeActStudio.MiniSTM32F4x1](https://github.com/WeActStudio/WeActStudio.MiniSTM32F4x1),
[stm32-base](https://stm32-base.org/boards/STM32F411CEU6-WeAct-Black-Pill-V2.0).

### STM32F429I-DISCO

![STM32F429I-DISCO](../images/stands/stm32f429i-disco.svg)

ЖК-дисплей 2,4″ занимает большую часть платы; STM32F429ZIT6 сверху не виден (показан пунктиром).
ST-LINK/V2 встроен (справа, USB Mini-B), гребёнки P1/P2. Источник:
[UM1670](https://www.st.com/resource/en/user_manual/dm00093903.pdf).

### WeAct AT32F403A V1.0

![WeAct AT32F403A](../images/stands/weact-at32f403a.svg)

Посадочное место и расположение деталей как у BlackPill: USB-C, NRST, BOOT0, KEY, C13, PWR, SWD.
Подключение совместимого МК — [совместимые МК](COMPATIBLE_MCU.md). Источник:
[WeActStudio.BlackPill](https://github.com/WeActStudio/WeActStudio.BlackPill).
