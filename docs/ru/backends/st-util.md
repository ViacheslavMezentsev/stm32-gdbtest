# st-util

[Backend](index.md) · [English](../../en/backends/st-util.md)

Открытый сервер проекта [stlink](https://github.com/stlink-org/stlink), backend `st-util`.
Это отдельный продукт от ST-LINK GDB Server: CubeProgrammer не нужен. Проверены Windows/Scoop
и Ubuntu 20.04/aarch64 на OrangePi. [Матрица](../API_ACCEPTANCE.md) задаёт точные границы приёмки.

## Две версии из практики

| Версия | Наблюдение | Вывод для нашего модуля |
| --- | --- | --- |
| Ubuntu `stlink-tools` 1.6.0+ds-1, `st-util v1.6.0` | Нет используемого `--freq`; в локальном опыте потребовалось иное кодирование serial. На F030 три варианта повторного reach/resume/stepi не дали ожидаемого изменения ticks | Не принята. В штатном backend обходов 1.6.0 нет; doctor с напечатанной версией не доказывает совместимость запуска |
| `st-util v1.9.0`, исходники `0697e5668df5f4f191c4d9f11803d5e995eb90df`, libusb 1.0.27 | Те же три навигационных опыта и BOOT/GPIO прошли; после правок lifecycle прошли полные наборы пяти STM32 через SSH | Проверенная комбинация для этого стенда; не обещание для любой сборки с баннером 1.9.0 |

В опыте 1.6.0 системная libusb была 1.0.23. Для выбранного 1.9.0 требовалась не ниже 1.0.24;
установлена отдельная 1.0.27. Одновременно изменились сервер, библиотека и параметры запуска:
причинная роль одного исправления IRQ/step не изолирована. Не ослабляли ожидания сценария ради PASS.

## TOML и команды

[Карта TOML](../BACKENDS.md#toml) · [шаблон стенда](../../../tests/firmware/stands/st-util.example.toml).
В `<profile>-st-util.remote.toml` укажите свои данные; `executable` — абсолютный путь **на хосте стенда**.
Замените `stand-user` в пути тоже. Локальный вариант не содержит `[remote]`.

```toml
[probe]
backend = "st-util"
serial = "REPLACE_WITH_24_HEX_DIGITS"
executable = "/home/stand-user/.local/stm32-gdbtest/stlink-1.9.0/bin/st-util"
speed_khz = 1000
flash = "if-different"
startup_timeout_s = 10

[remote]
host = "stand-host"
user = "stand-user"
identity_file = "~/.ssh/id_ed25519_stand"
```

На Windows можно указать `%USERPROFILE%/scoop/apps/stlink/current/bin/st-util.exe`.
Серийный номер —24 hex-цифры; runner передаёт верхний регистр, не индекс устройства.
Фрагмент target schema 2 (полный профиль MCU остаётся обязательным):

```toml
[st-util]
reset_halt = "monitor reset"
```

Секция необязательна. `reset_run` в ней запрещён. Setup — `set mem inaccessible-by-default off`;
завершение/recovery — `monitor reset`, `monitor resume`, `disconnect`. Команды ST или OpenOCD
сюда не копируются. Запуск: `--multi --no-reset --serial SERIAL --freq 1000k --listen_port PORT`.
Runner выделяет порт; не запускайте второй сервер на том же probe. `--multi` позволяет recovery-клиент,
не shared mode нескольких тестов. Блокировка ST-Link общая с OpenOCD и сервером ST.
Сервер слушает все сетевые интерфейсы; `[remote]` использует SSH-туннель модуля, не `st-server`/`--remote`.

## Сборка 1.9.0 на Ubuntu 20.04

Рецепт повторяет параметры установленной и проверенной сборки OrangePi; команды сведены по
исходникам/CMakeCache, заново здесь не исполнялись. Сборка native, не arm-none-eabi:
нужны GCC с C17, CMake≥3.21 (проверен 3.28.3) и libusb≥1.0.24. Системные CMake 3.16/libusb 1.0.23
не подходят. Сначала установите [окружение стенда](../LINUX_STAND.md), предоставляющее `env.sh`.
GUI не нужен; пример рассчитан на headless-стенд без GTK development packages.

Системный `/usr/bin/st-util` и системная libusb сохраняются. Сборка устанавливается без sudo в
пользовательские префиксы; если там уже есть используемая сборка, сначала сохраните её или выберите
другие префиксы. Не переустанавливайте библиотеки во время работающего аппаратного теста.

```bash
# On the Ubuntu 20.04 stand; prerequisite packages need administrator rights.
sudo apt update
sudo apt install build-essential pkg-config libudev-dev git curl bzip2
```

```bash
(
set -eu
# Install the module's Linux stand environment first (CMake 3.28.3 in our checks).
. "$HOME/.local/stm32-gdbtest/env.sh"
cmake --version
gcc --version

backend_prefix="$HOME/.local/stm32-gdbtest/stlink-1.9.0"
usb_prefix="$HOME/.local/stm32-gdbtest/libusb-1.0.27"
source_dir="$(mktemp -d "$HOME/stlink-build.XXXXXX")"
cd "$source_dir"

curl --fail --location --output libusb-1.0.27.tar.bz2 \
  https://github.com/libusb/libusb/releases/download/v1.0.27/libusb-1.0.27.tar.bz2
printf '%s  %s\n' \
  fffaa41d741a8a3bee244ac8e54a72ea05bf2879663c098c82fc5757853441575 \
  libusb-1.0.27.tar.bz2 | sha256sum --check -
tar -xf libusb-1.0.27.tar.bz2
(
  cd libusb-1.0.27
  ./configure --prefix="$usb_prefix" --libdir="$usb_prefix/lib" --disable-static
  make -j2
  make install
)

git clone https://github.com/stlink-org/stlink.git stlink
# Exact source revision of the tested 1.9.0 build, not a floating branch.
git -C stlink checkout --detach 0697e5668df5f4f191c4d9f11803d5e995eb90df
git -C stlink rev-parse HEAD
export PKG_CONFIG_PATH="$usb_prefix/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
pkg-config --modversion libusb-1.0

cmake -S stlink -B stlink-build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$backend_prefix" \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DLIBUSB_INCLUDE_DIR="$usb_prefix/include/libusb-1.0" \
  -DLIBUSB_LIBRARY="$usb_prefix/lib/libusb-1.0.so" \
  -DCMAKE_INSTALL_RPATH="$backend_prefix/lib;$usb_prefix/lib" \
  -DSTLINK_MODPROBED_DIR="$backend_prefix/share/modprobe.d" \
  -DSTLINK_UDEV_RULES_DIR="$backend_prefix/share/udev/rules.d"
cmake --build stlink-build --parallel 2
cmake --install stlink-build

"$backend_prefix/bin/st-util" --version
ldd "$backend_prefix/bin/st-util"
ldd "$backend_prefix/lib/libstlink.so.1"
sha256sum "$backend_prefix/bin/st-util" "$backend_prefix/lib/libstlink.so.1" \
  "$usb_prefix/lib/libusb-1.0.so.0"
printf 'Sources and build logs: %s\n' "$source_dir"
)
```


Для libusb нужен release-архив `.tar.bz2` с готовым `configure`, а не автоматически созданный GitHub
source zip/tar.gz. [Пояснение upstream](https://github.com/libusb/libusb/releases/tag/v1.0.27).
Параметры выбранной ревизии stlink: [CMakeLists](https://github.com/stlink-org/stlink/blob/0697e5668df5f4f191c4d9f11803d5e995eb90df/CMakeLists.txt).

`ldd` должен показать libstlink из префикса stlink 1.9.0 и libusb из префикса 1.0.27, без `not found`.
Проверяйте также libstlink: зависимости могут быть транзитивными. Одного `st-util --version` недостаточно.
`PKG_CONFIG_PATH` и явные LIBUSB-пути не дают CMake взять старые заголовки/библиотеку; RPATH позволяет
запускать выбранный бинарник без глобальной замены `LD_LIBRARY_PATH`/системной libusb.

Параметры STLINK_UDEV_RULES_DIR/STLINK_MODPROBED_DIR предотвращают запись `cmake --install`
в `/lib/udev/rules.d` и `/etc/modprobe.d`. Это только сохранённые файлы: пользовательские правила
сами не становятся активными. На нашем стенде USB-права уже были настроены. На новом стенде
администратор настраивает [udev и доступ](../LINUX_STAND.md) и переподключает USB вне тестирования.
Не запускайте runner под sudo как замену настройке прав. `tools/linux_stand.py` пока не ставит st-util.

## Что потребовало изменений модуля

| Наблюдение | Изменение и граница |
| --- | --- |
| Карта памяти 1.9.0 не включала заводской регистр F411 `0x1FFF7A22` | Setup разрешает GDB отправить чтение за пределами карты; identity, размер Flash и проверка образа не отключаются |
| После внешнего timeout сервер ещё не готов принять recovery | Ожидание новой полной строки `Listening at *:PORT...` после последнего `GDB connected.`; старый стартовый маркер недостаточен |
| Реальный Listening оканчивается многоточием | Парсер принимает вариант с многоточием и без него, только полную строку текущего порта/попытки |
| F103: libusb assertion при завершении; helper мог скрыть поздний код сервера | Ожидание idle перед остановкой, reap до публикации фактического exit; исходный статус хранится как `status_before_cleanup` |
| Отсутствие читателя SSH могло блокировать вывод helper | Ограниченный неблокирующий вывод и локальное наблюдение idle; потерянное подтверждение остаётся ERROR |
| Длинная матрица ADC через SSH занимала около 60с | Бюджет конкретных сценариев F4 увеличен до 120с; общий тайм-аут и проверки не ослаблены |

Recovery idle — до 5с, одна попытка recovery — до 10с; shutdown idle — до 5с. Helper независимо
наблюдает idle и при потере SSH; затем TERM 3с, KILL 5с, reap 5с, runner ждёт SSH до 25с.
В удалённом штатном исходе st-util требуется фактический exit 0 и подтверждённый idle.
Неизвестный exit, SIGKILL, heartbeat timeout или отсутствие маркера — ERROR.
Это ограниченная попытка cleanup, а не доказательство безопасности USB при любой аварии.

## Проверка установки и разбор отказа

Порядок: `--version`/`ldd` → `doctor --stand …` → `run --prepare-only` → BOOT/GPIO →
жизненный цикл с timeout/recovery → полный набор на согласованной плате. Команды CLI и
генерация session.json — [API](../API.md); состояние сборки не заменяет HW PASS.

`server.log`, `tunnel.log`, `gdb.log`, `recovery.log` и `result.json` сохраняются вместе.
`cannot recv: -2` наблюдалось при disconnect с последующим Listening/exit 0, но не является
универсально безвредным сообщением. Проверяйте фазу, фактический exit, idle и результат следующего подключения.
Пустой/бинарный USB serial может дать WARN doctor; на Windows capture используйте `python -X utf8`.
При USB ERROR сохраните отказ, проверьте процессы/lock и восстанавливайте только после возврата доступа.
