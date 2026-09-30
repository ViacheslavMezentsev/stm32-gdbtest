# Linux-стенд

[Документация](index.md) → Linux-стенд · [English](../en/LINUX_STAND.md)

Аппаратный запуск работает на Linux x86_64 и aarch64 с glibc ≥ 2.31, то есть и на
Ubuntu 20.04. Целевой стенд проверки — Orange Pi 5 с Ubuntu 20.04 (aarch64). Runner,
GDB-сервер и отладчик находятся на одном компьютере, либо GDB-сервер работает на
Orange Pi, а runner — на Windows или в WSL ([удалённый GDB-сервер](#удалённый-gdb-сервер-windows-или-wsl--orange-pi)).
Требования — п. 5.4.8–5.4.11, 5.17, 5.18 и 6.10 [ТЗ](../TECHNICAL_SPECIFICATION.md).

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
устанавливает `/opt/SEGGER/JLink` и свои правила udev. Проверены версии 8.32 (Windows,
Orange Pi 5) и 9.80 (Orange Pi 5). После подключения отладчиков `doctor` показывает найденные устройства,
их серийные номера и доступ к `/dev/bus/usb`.

**J-Link STLink** (встроенный ST-Link Nucleo, перепрошитый в J-Link) при подключении
к цели показывает графическое окно с условиями использования: оно работает только с
целями STM32, и эти условия нужно подтвердить галочкой. Консольный сервер окна не
показывает: без рабочего стола подключение ждёт около 10 с — дольше предела
готовности сервера по умолчанию — и запуск завершается ERROR «GDB server startup timed
out». Подтвердите окно один раз в графическом сеансе (монитор или удалённый рабочий
стол): `JLinkExe -USB <serial>`, затем `connect`. На Orange Pi 5 после этого F030R8
прошёл 10/10; сохраняется ли подтверждение после перезагрузки или переподключения, не
проверялось. Если окно подтвердить нельзя, задайте в стенде `startup_timeout_s = 30`.
J-Link CE и ST-Link такого окна не показывают.

ST-LINK GDB Server (STM32CubeCLT) для aarch64 не выпускается: на Orange Pi 5
используются backend `openocd` и `jlink`. На Linux x86_64 доступны все три.

## Локальный стенд и запуск

Скопируйте шаблон из `tests/firmware/stands/*.example.toml` в `*.local.toml` (такие
файлы не коммитятся) и укажите serial из вывода `doctor`. Для OpenOCD достаточно
`executable = "openocd"` — из `PATH` окружения; для J-Link —
`executable = "/opt/SEGGER/JLink/JLinkGDBServerCLExe"`.

```sh
. ~/.local/stm32-gdbtest/env.sh
python3 -B -m stm32_gdbtest doctor --stand tests/firmware/stands/f411ce-openocd.local.toml
python3 -B tests/firmware/run_hw.py --profile f411ce --stand tests/firmware/stands/f411ce-openocd.local.toml
```

`run_hw.py` перезаписывает Flash; итог — `build/hw/<профиль>-<стенд>/summary.json`
([проверки и CI](testing.md)). Для своего проекта окружение то же: CMake-интеграция
находит `arm-none-eabi-gdb-py3` в `PATH`.

## Блокировка и процессы

Отладчик защищается файлом `flock` в `/tmp/stm32-gdbtest-locks` (или в
`STM32_GDBTEST_LOCK_DIR`), общим для всех пользователей и проектов хоста. Сервер и
GDB работают в отдельной группе процессов и останавливаются вместе с потомками.
Подробности и поведение после аварии — [владение отладчиком](DEBUGGER_OWNERSHIP.md#linux).

## Удалённый GDB-сервер (Windows или WSL → Orange Pi)

Runner, GDB и сборка остаются на компьютере разработчика (Windows или WSL), а
GDB-сервер и отладчики — на Orange Pi. Для этого в стенд добавляется таблица
`[remote]`. Runner открывает одну SSH-сессию: она пробрасывает локальный порт на порт
сервера на Orange Pi и запускает там небольшой вспомогательный скрипт. Скрипт берёт
ту же блокировку отладчика, что и локальные запуски на Orange Pi, запускает сервер и
останавливает его, когда сессия закрывается или обрывается. Runner каждые 2 с шлёт в
сессию сигнал присутствия: если связь пропала без закрытия соединения, сервер
останавливается через 15 с тишины. Копия модуля на Orange Pi
не нужна, достаточно окружения стенда (для xPack OpenOCD) и ПО J-Link. Пароли не
поддерживаются: только SSH-ключ и заранее известный ключ хоста.

Один раз на Windows (PowerShell):

```powershell
ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\id_ed25519_stand     # пустая фраза или ssh-agent
type $env:USERPROFILE\.ssh\id_ed25519_stand.pub | ssh orangepi@<хост> "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
ssh -i $env:USERPROFILE\.ssh\id_ed25519_stand orangepi@<хост> exit   # принять ключ хоста; пароль больше не спрашивается
```

Во второй команде пароль вводится в последний раз. Ключ с фразой-паролем работает
только через `ssh-agent` (служба OpenSSH Authentication Agent в Windows): runner
запускает SSH без интерактивного ввода. После проверки входа по ключу вход по паролю
на Orange Pi можно отключить (`PasswordAuthentication no` в `/etc/ssh/sshd_config`,
затем `sudo systemctl restart ssh`).

Стенд — копия [шаблона](../../tests/firmware/stands/remote.example.toml):

```toml
[probe]
backend = "jlink"
serial = "<serial>"
executable = "/opt/SEGGER/JLink/JLinkGDBServerCLExe"   # путь на Orange Pi

[remote]
host = "<хост>"                  # адрес, имя или псевдоним из ~/.ssh/config
user = "orangepi"
identity_file = "~/.ssh/id_ed25519_stand"       # или %USERPROFILE%/.ssh/…
```

Ключи `[remote]`:

| Ключ | Значение |
| --- | --- |
| `host` | Адрес, имя хоста или псевдоним из `~/.ssh/config` (обязателен) |
| `user` | Пользователь на хосте стенда; по умолчанию — из конфигурации SSH |
| `port` | Порт SSH, 1…65535, по умолчанию 22 |
| `identity_file` | Путь к закрытому ключу; `~`, `%USERPROFILE%`, `$HOME` раскрываются (например, `~/.ssh/id_ed25519_stand`); без него — ключи агента и `~/.ssh` |
| `env_script` | Скрипт окружения на хосте стенда; не подключился — отказ с кодом 97. По умолчанию подключается `~/.local/stm32-gdbtest/env.sh`, если он есть |
| `ssh` | Клиент SSH, по умолчанию `ssh` из `PATH` |

Ключи с паролями (`password`, `passphrase`, `secret`, `token`) отклоняются. На хосте
стенда нужен только `python3` ≥ 3.8 (подходит системный Python Ubuntu 20.04). Порт
сервера на хосте стенда выбирается случайно из 40000–59999; готовности ждут
`startup_timeout_s` + 10 с на SSH. `STM32_GDBTEST_LOCK_DIR` на хосте стенда действует,
только если его экспортирует `env_script` или `env.sh`: вспомогательный скрипт
запускается неинтерактивно.

`executable` для OpenOCD — просто `openocd`: перед запуском сервера на Orange Pi
подключается `~/.local/stm32-gdbtest/env.sh` (другой путь — `env_script`). Проверка и
запуск — с Windows, как для локального стенда:

```powershell
python -B -m stm32_gdbtest doctor --stand tests/firmware/stands/f411ce-remote.local.toml
python -B tests/firmware/run_hw.py --profile f411ce --stand tests/firmware/stands/f411ce-remote.local.toml
```

`doctor` проверяет через ту же SSH-сессию Python, сервер, каталог блокировок и
отладчики USB на Orange Pi. В каталоге запуска появляется `tunnel.log` (журнал SSH),
а журналы сервера с Orange Pi попадают в `server.log`. Частые ошибки — в
[памятке](HOWTO.md#удалённый-gdb-сервер-по-ssh).

## WSL2 и usbipd-win

Отладчик можно пробросить в дистрибутив WSL2 (`usbipd bind` и `usbipd attach --wsl`
в Windows); дальше порядок тот же, что на Linux. Блокировка WSL не пересекается с
mutex Windows, поэтому один отладчик нельзя одновременно использовать из Windows и
WSL. Этот сценарий на оборудовании не проверялся: на компьютере владельца usbipd-win
конфликтует с фильтрами USB других программ (предупреждения `usbipd list` о USBPcap и
`nxusbf`), подключение срывается, возможен сбой Windows. Проверенный путь для WSL —
[удалённый сервер](#удалённый-gdb-сервер-windows-или-wsl--orange-pi) на Orange Pi.

## Ограничения

- Установка, host-тесты, `doctor`, сборка и подготовка проверяются в CI (задание
  `linux-stand`, Ubuntu 20.04 x86_64 и aarch64). Аппаратные результаты на Orange Pi 5 —
  локально и с Windows по SSH — в [текущем состоянии](STATUS.md).
- Аварийное завершение runner не останавливает группу процессов сервера: проверьте
  `pgrep -a openocd` и `pgrep -a JLink` перед повтором.
- xPack OpenOCD 0.12.0-7 предупреждает об устаревших `tcl_port`, `telnet_port`,
  `gdb_port`; команды оставлены совместимыми с OpenOCD 0.12.0.
