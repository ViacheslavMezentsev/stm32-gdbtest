# Подготовленные запуски, аппаратный CI и прогоны 24/7

[Документация](index.md) → Аппаратный CI · [English](../en/HARDWARE_CI.md)

Сборка и подготовка выполняются там, где есть toolchain (рабочий компьютер, CI), а
запуск — на стенде, где подключены отладчики. Между ними передаётся один файл —
**пакет подготовленного запуска**. На нём построены ручной перенос, аппаратный CI на
self-hosted раннере GitHub и повторяющиеся прогоны на стенде. Требования — п. 5.19,
8.21, 8.22 [ТЗ](../TECHNICAL_SPECIFICATION.md), метод — [DDTT](DDTT.md), разделы 6.7, 6.8.

## Пакет подготовленного запуска

```powershell
python -B -m stm32_gdbtest pack --session <build>/hwtest/session.json --output build/packages/f411ce.zip
```

`pack` сначала выполняет для каждого сценария подготовку без оборудования
(`run --prepare-only`: снимок ELF, build manifest, контракты, образ) и при любом
ERROR пакет не пишет. Затем в zip попадают:

| Файл | Содержимое |
| --- | --- |
| `ddtt-package.json` | Схема 1: версия модуля, время создания, SHA-256 ELF, сценарии и их метаданные, итоги подготовки, SHA-256 каждого файла |
| `firmware.elf` | ELF с отладочной информацией |
| `build-manifest.json` | Build manifest, если он есть |
| `profile/target.toml`, `profile/tests/…` | Профиль MCU, сценарии, `contracts.json`, `requirements.md` |
| Файлы `--include` | Вспомогательные модули проекта, которые импортируют сценарии (пути относительно корня проекта) |

`--test ID` (можно повторять) оставляет в пакете только выбранные сценарии. В пакет
попадает каталог `Tests` сценариев и описание MCU, даже если оно задано отдельным
файлом (`PROFILE`).

Запуск на стенде — по пакету вместо `session.json`:

```sh
python3 -B -m stm32_gdbtest run --package f411ce.zip --test HW_CI_BOOT --stand f411ce.local.toml
```

Перед запуском проверяется SHA-256 каждого файла; лишний, изменённый или опасный
путь (`..`, абсолютный) — отказ. Пакет распаковывается в `--workdir` (по умолчанию
`build/ddtt-packages/<хэш>`), GDB берётся на стенде (`--gdb` → `STM32_GDBTEST_GDB` →
`PATH` → `ARM_TOOLCHAIN_ROOT`). Отчёт получает поле `package` с хэшем, именем и
временем создания пакета. Пересборки на стенде нет; подготовка перед сервером
повторяется уже с его GDB.

Для CI-прошивок то же делает `run_hw.py --package <файл> ...`: шаг `build` проверяет,
что пакет содержит сценарии CI, остальные шаги идут как обычно.

## Аппаратный CI на self-hosted раннере

Workflow **Hardware** (`.github/workflows/hardware.yml`) запускается только вручную
(Actions → Hardware → Run workflow): выбираются профили и при необходимости шаги.

1. Задание `prepare` на `ubuntu-24.04` ставит закреплённый toolchain
   (`tools/linux_stand.py`), собирает CI-прошивки, выполняет CTest `host` и `pack` и
   сохраняет пакеты артефактом `ddtt-packages`.
2. Задание `hardware` на раннере с метками `self-hosted, linux, ARM64, stm32-stand`
   скачивает пакеты и для каждого профиля выполняет `doctor` и `run_hw.py --package`.
   Результаты — артефакт `hardware-results`.

Стенды раннера лежат вне репозитория: `$STM32_GDBTEST_STANDS_DIR/<профиль>.toml`, по
умолчанию `~/.config/stm32-gdbtest/stands/f411ce.toml` и т. д.

### Установка раннера на Orange Pi

Нужны [окружение стенда](LINUX_STAND.md) и доступ к USB. В GitHub: Settings → Actions →
Runners → New self-hosted runner → Linux, ARM64; GitHub покажет команды загрузки и
`config.sh` с одноразовым токеном — токен не сохраняйте в файлах. При настройке
добавьте метку:

```sh
./config.sh --url https://github.com/<владелец>/stm32-gdbtest --token <токен> --labels stm32-stand
echo "STM32_GDBTEST_STANDS_DIR=$HOME/.config/stm32-gdbtest/stands" >> .env
sudo ./svc.sh install "$USER" && sudo ./svc.sh start
```

Службе раннера графический сеанс недоступен: в стенде J-Link STLink задайте
`startup_timeout_s = 30` или подтвердите окно условий заранее
([памятка](HOWTO.md#linux-стенд-и-orange-pi)).

### Безопасность

Репозиторий публичный, а раннер имеет доступ к стенду и сети. Поэтому:

- workflow запускается только вручную, не на `pull_request` и не на `push`;
- в Settings → Actions → General оставьте требование подтверждения запусков для
  внешних участников;
- раннер работает под отдельным пользователем без sudo, только с доступом к USB;
- стенды и ключи раннера не хранятся в репозитории.

Удалить раннер: `sudo ./svc.sh stop && sudo ./svc.sh uninstall`, затем
`./config.sh remove --token <токен>` (токен удаления выдаёт GitHub на странице раннера).

## Прогоны 24/7

`run_hw.py --repeat N` повторяет выбранные шаги N раз, `--repeat 0` — до Ctrl+C. Шаг
`build` выполняется один раз. Каждая итерация сохраняет `iterations/NNNNN.json`, а
`soak.json` — счётчики: итерации, успешные итерации, отказы по шагам, первый отказ,
время последней итерации, признак прерывания.

```sh
. ~/.local/stm32-gdbtest/env.sh
python3 -B tests/firmware/run_hw.py --profile f411ce --stand tests/firmware/stands/f411ce-openocd.local.toml \
  --steps boot gpio timeout after-recovery --repeat 0
```

Для прогона без открытого терминала подойдёт `tmux`/`screen` или пользовательская
служба systemd (`systemd-run --user --unit=ddtt-soak …`). Шаги с записью Flash
(`full-a5`, `full-ff`) изнашивают память: для длительных прогонов выбирайте шаги без
записи.

## Сохранение результатов пакетов (rc.2)

При повторном run --package исходники распаковываются в новый
`<workdir>/<16 знаков SHA-256>/sessions/session-*`. Отчёты каждого запуска остаются
в его `<workdir>/<16 знаков SHA-256>/sessions/session-*/runs`. Пути сессии следует брать из
метаданных, не конструировать как `<хэш>/firmware.elf`. Старые пакеты schema 1
читаются без изменений; API_VERSION=1. Каталог источников сохраняется для
разбора ошибок; автоматической очистки нет. Удалять старые build можно только
после сохранения нужных доказательств и завершения использующих их запусков.

До исправления новое открытие пакета удаляло весь каталог хэша, включая runs.
Утерянные JSON не восстанавливаются из summary: нужен повтор проверки.

## Выбор нового набора API 0.4.0

Hardware → Run workflow: выберите выпускную ветку, `suite=api040`, профили
`f030r8 f103c8 f401cc f411ce f429zi`; поле `steps` оставьте пустым.
`suite=lifecycle` сохраняет прежние десять этапов `run_hw.py`; default — lifecycle.
Новый режим не запускает старые аппаратные сценарии и не является полным повтором приёмки API.

Prepare собирает ту же прошивку и создаёт два пакета на профиль через `tests/firmware/api040.py pack`:
четыре сценария с включённой возможностью и один SKIP с выключенной. Capture включён в обеих
конфигурациях до упаковки; capsule после проверки хешей не меняется. На стенде `api040.py run`
проверяет 4 PASS + 1 SKIP (77), JSON/JUnit, хеш и принадлежность records, типы данных и finally.
Успешный export не скрывает отказ аппаратного сценария. После отказа doctor MCU не запускается.

`hardware-results` содержит JSON, JUnit XML, CSV, HTML, журналы и TSV с кодами каждого профиля.
Отчёты лежат в `api040/<профиль>/<попытка>/report/campaign.html`, сводка — рядом в summary.json.
Каждая попытка получает отдельный каталог. Скачивайте весь артефакт, сохраняя структуру;
для повторного verify используйте каталог конкретной попытки как `--root`.
При отказе сохраняются частичные результаты; отсутствие отчёта остаётся ошибкой.

Локальная проверка тех же команд (пути являются примерами):

```text
python tests/firmware/api040.py pack --session <session.json> --output <новый-каталог-пакетов>
python tests/firmware/api040.py run --enabled-package <enabled.zip> --disabled-package <disabled.zip> --stand <stand.toml> --output build/hw/api040/manual
```

В CI-стендах на OrangePi используйте локальные `[probe]`, без `[remote]`: runner и GDB находятся
на том же хосте. Для принятой конфигурации st-util задайте абсолютный путь к сборке 1.9.0,
серийный номер текущего ST-Link, speed_khz=1000 и flash=if-different.
[Установка st-util](backends/st-util.md) · [Сценарии и границы проверки](API040_SCENARIOS.md).

Проверка подготовки 10.10.2026: пакеты F411 с Windows исполнены локально на OrangePi
через st-util 1.9.0 — 4 PASS + 1 ожидаемый SKIP; export/verify/report успешны. Doctor пяти
CI-профилей прошёл. Это репетиция драйвера и пакетов, не запуск GitHub Actions.

Внешний конечный диспетчер пакетов: [stand_loop](STAND_LOOP.md). Target API не меняется; старые команды run/pack остаются прежними.

Hardware теперь принимает `at32f403a` в обоих наборах и включает его в шесть профилей по умолчанию.
Prepare устанавливает закреплённый SDK через `tools/vendor_sdk.py` с SHA256 в `$RUNNER_TEMP/at32-sdk`.
На OrangePi требуется `$STM32_GDBTEST_STANDS_DIR/at32f403a.toml` (по умолчанию
`~/.config/stm32-gdbtest/stands/at32f403a.toml`): backend=jlink, серийник вашего J-Link и путь к серверу.
Для отдельной проверки: profiles=`at32f403a`, suite=`api040`, steps оставить пустым.
Локальная приёмка платы не заменяет запуск обновлённого workflow на GitHub.
