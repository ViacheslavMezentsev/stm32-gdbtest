# Linux-стенд

[Документация](index.md) → Linux-стенд · [English](../en/LINUX_STAND.md)

Аппаратный запуск работает на Linux x86_64 и aarch64 с glibc ≥ 2.31, то есть и на
Ubuntu 20.04. Целевой стенд проверки — Orange Pi 5 с Ubuntu 20.04 (aarch64). Runner,
GDB-сервер и отладчик находятся на одном компьютере; удалённый сервер по SSH пока
не поддерживается (вопрос 11.2.18 [ТЗ](../TECHNICAL_SPECIFICATION.md)). Требования —
п. 5.4.8–5.4.11, 5.17 и 6.10 ТЗ.

## Окружение без root

Системные пакеты Ubuntu 20.04 не подходят: Python 3.8 (модулю нужен 3.11), CMake 3.16
(нужен 3.25), OpenOCD 0.10 без `interface/stlink.cfg`. Сценарий
`tools/linux_stand.py` ставит закреплённые версии в каталог пользователя (по
умолчанию `~/.local/stm32-gdbtest`) и не меняет систему:

| Компонент | Версия | Источник |
| --- | --- | --- |
| Python | 3.11.16 | python-build-standalone (тот же, что использует uv) |
| CMake / Ninja | 3.28.3 / 1.12.1 | Kitware, ninja-build |
| GNU Arm GCC с GDB-Python | xPack 13.3.1-1.1 (GDB 14.2.90, Python 3.11.4) | xPack |
| OpenOCD | xPack 0.12.0-7 | xPack |
| CMSIS | STM32CubeF0 1.11.6, F1 1.8.7, F4 1.28.3 (`Drivers/CMSIS`) | GitHub STMicroelectronics |

Архивы для x86_64 и aarch64 закреплены по SHA-256 в
[tools/linux-stand.lock.json](../../tools/linux-stand.lock.json); версии совпадают с
[CI](testing.md). Сам сценарий выполняется системным Python ≥ 3.8. Нужны `curl`,
`tar` и `git`; загрузки остаются в `<каталог>/downloads`, повторный запуск пропускает
установленные компоненты.

```sh
sudo apt install -y ca-certificates curl git python3   # если чего-то нет
git clone https://github.com/ViacheslavMezentsev/stm32-gdbtest.git
cd stm32-gdbtest
python3 tools/linux_stand.py install
. ~/.local/stm32-gdbtest/env.sh
python3 -B -m stm32_gdbtest doctor
```

`env.sh` добавляет инструменты в начало `PATH` текущей оболочки (после него
`python3` — это Python 3.11 окружения) и задаёт `ARM_TOOLCHAIN_ROOT`,
`STM32CUBE_REPOSITORY`, `STM32_GDBTEST_GDB`. Другой каталог — `--prefix` или
`STM32_GDBTEST_PREFIX`; часть компонентов — `--only python cmake …`; проверка без
установки — `python3 tools/linux_stand.py verify`.

## Доступ к USB и J-Link (владелец стенда)

Эти шаги требуют root и выполняются вручную один раз:

```sh
# ST-Link: правила udev из xPack OpenOCD
sudo cp ~/.local/stm32-gdbtest/xpack-openocd-0.12.0-7/openocd/contrib/60-openocd.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

ПО J-Link для Linux (для Orange Pi 5 — пакет `arm64`) скачивается с сайта SEGGER
после принятия лицензии и ставится `sudo dpkg -i JLink_Linux_V…_arm64.deb`; пакет
устанавливает `/opt/SEGGER/JLink` и свои правила udev. На Windows-стендах проверена
версия 8.32. После подключения отладчиков `doctor` показывает найденные устройства,
их серийные номера и доступ к `/dev/bus/usb`.

ST-LINK GDB Server (STM32CubeCLT) для aarch64 не выпускается: на Orange Pi 5
используются backend `openocd` и `jlink`. На Linux x86_64 доступны все три.

## Локальный стенд и запуск

Скопируйте шаблон из `Tests/firmware/stands/*.example.toml` в `*.local.toml` (такие
файлы не коммитятся) и укажите serial из вывода `doctor`. Для OpenOCD достаточно
`executable = "openocd"` — из `PATH` окружения; для J-Link —
`executable = "/opt/SEGGER/JLink/JLinkGDBServerCLExe"`.

```sh
. ~/.local/stm32-gdbtest/env.sh
python3 -B -m stm32_gdbtest doctor --stand Tests/firmware/stands/f411ce-openocd.local.toml
python3 -B Tests/firmware/run_hw.py --profile f411ce --stand Tests/firmware/stands/f411ce-openocd.local.toml
```

`run_hw.py` перезаписывает Flash; итог — `build/hw/<профиль>-<стенд>/summary.json`
([проверки и CI](testing.md)). Для своего проекта окружение то же: CMake-интеграция
находит `arm-none-eabi-gdb-py3` в `PATH`.

## Блокировка и процессы

Отладчик защищается файлом `flock` в `/tmp/stm32-gdbtest-locks` (или в
`STM32_GDBTEST_LOCK_DIR`), общим для всех пользователей и проектов хоста. Сервер и
GDB работают в отдельной группе процессов и останавливаются вместе с потомками.
Подробности и поведение после аварии — [владение отладчиком](DEBUGGER_OWNERSHIP.md#linux).

## WSL2 и usbipd-win

Отладчик можно пробросить в дистрибутив WSL2 (`usbipd bind` и `usbipd attach --wsl`
в Windows); дальше порядок тот же, что на Linux. Блокировка WSL не пересекается с
mutex Windows, поэтому один отладчик нельзя одновременно использовать из Windows и
WSL. Этот сценарий на оборудовании ещё не проверялся (вопрос 11.2.20 ТЗ).

## Ограничения

- Установка, host-тесты, `doctor`, сборка и подготовка проверяются в CI (задание
  `linux-stand`, Ubuntu 20.04 x86_64 и aarch64). Аппаратные результаты на Orange Pi 5
  отражаются в [текущем состоянии](STATUS.md) после прогона.
- Аварийное завершение runner не останавливает группу процессов сервера: проверьте
  `pgrep -a openocd` и `pgrep -a JLink` перед повтором.
- xPack OpenOCD 0.12.0-7 предупреждает об устаревших `tcl_port`, `telnet_port`,
  `gdb_port`; команды оставлены совместимыми с OpenOCD 0.12.0.
