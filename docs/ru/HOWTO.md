# Памятка: частые команды и проблемы

[Документация](index.md) → Памятка · [English](../en/HOWTO.md)

Сюда заглядывают разработчик и агент, когда что-то не работает, прежде чем искать
новое решение. Для каждой проблемы указано, как её исправить и как вернуть прежнее
состояние. Правила проекта — в [сопровождении](maintenance.md); здесь только команды.
Найденное новое решение частой проблемы добавляется сюда в том же коммите (RU и EN).

Условные обозначения: **PS** — PowerShell на Windows, **sh** — оболочка Linux
(Orange Pi, WSL). Команды git одинаковы в обеих, кроме кавычек (раздел «Псевдоним
`git land`»).

## Git: рабочий цикл без PR

Ветка `<агент>/<задача>` создаётся от свежего main и после проверок сливается в main
перемоткой (fast-forward). Порядок действует для одного разработчика с агентами; при расширении команды его пересматривают. Слить без PR в веб-интерфейсе GitHub нельзя, и
автоудаление веток GitHub работает только для PR, поэтому слияние и уборка делаются
локально.

```
git switch main
git pull --ff-only
git switch -c claude/<задача>          # новая ветка
# … коммиты …
git push -u origin claude/<задача>     # CI: дождаться зелёных Docs и Offline
git land claude/<задача>               # перемотать main, отправить, удалить ветку
```

Перемотка не создаёт merge-коммит: в main попадают те же подписанные коммиты, и
GitHub показывает их Verified. Если ветка отстала от main, `git land` остановится на
`--ff-only`, ничего не изменив. Тогда ветку переносят на свежий main и снова
подписывают:

```
git switch claude/<задача>
git rebase -S origin/main              # конфликты: исправить, git add, git rebase --continue
git push --force-with-lease            # только для своей неслитой ветки
```

Force push в main и в чужие ветки запрещён.

### Псевдоним `git land`

Установка — одинарные кавычки обязательны: в PowerShell внутри двойных кавычек `$`
подставляется самим PowerShell, а `\"` не экранирует кавычку.

```powershell
git config --global --unset-all alias.land   # если уже был; ошибка «no such section» не страшна
git config --global alias.land '!f() { b=${1:-$(git branch --show-current)}; git fetch origin && git switch main && git merge --ff-only origin/main && git merge --ff-only $b && git push --atomic origin main :$b && git branch -d $b; }; f'
git config --global --get-all alias.land     # ровно одна строка с b=${1:-$(git branch --show-current)}
```

Ту же команду в sh можно выполнить без изменений. Что делает `git land <ветка>`:
`fetch` → перемотка main до `origin/main` → перемотка main до ветки → одним атомарным
push отправка main и удаление ветки на GitHub → удаление локальной ветки.

| Проблема | Решение |
| --- | --- |
| `syntax error: unexpected end of file`, в ошибке `b=;` | Псевдоним записан в двойных кавычках из PowerShell. Удалить (`--unset-all`) и записать заново в одинарных |
| `warning: alias.land has multiple values` | `git config --global --unset-all alias.land`, затем записать заново; либо `git config --global --edit` и удалить лишние строки `land = …` |
| `fatal: Not possible to fast-forward` | Ветка отстала от main: `git rebase -S origin/main` (выше) |
| Push отклонён: protected branch, required pull request | В Settings → Rules снять требование PR для main или разрешить себе обход (bypass) |

Вернуть как было: удалить псевдоним — `git config --global --unset-all alias.land`.

### Уборка веток

```
git fetch --prune                                  # убрать ссылки на удалённые на GitHub ветки
git branch -r --merged origin/main                 # слитые ветки на GitHub
git push origin --delete <ветка> [<ветка> …]       # удалить на GitHub
git branch -vv                                     # локальные; [gone] — на GitHub уже нет
git branch -d <ветка>                              # удалить слитую локальную
git branch -D <ветка>                              # удалить, если хэш отличается, а содержимое уже в main
```

На другом компьютере (Orange Pi) после слияния:

```sh
git switch main && git pull --ff-only && git branch -D <ветка> && git fetch --prune
```

### Как вернуть состояние

| Ситуация | Команда |
| --- | --- |
| Отменить незакоммиченные правки в файлах | `git restore <файл>` или `git restore .` |
| Убрать файл из индекса, сохранив правки | `git restore --staged <файл>` |
| Удалить неотслеживаемые файлы | сначала `git clean -n` (что удалится), затем `git clean -f`; `*.local.toml` игнорируются и не удаляются без `-x` — не используйте `-x` |
| Отменить последний неотправленный коммит, сохранив правки | `git reset --soft HEAD~1` |
| Локальный main испорчен, но ещё не отправлен | `git switch main && git reset --hard origin/main` |
| Удалили ветку по ошибке | `git reflog` → найти хэш → `git branch <ветка> <хэш>`; на GitHub вернуть: `git push origin <ветка>` |
| Отменить коммит, уже отправленный в main | `git revert <хэш>` новым подписанным коммитом, затем обычный цикл; историю main не переписывать |
| Прервать неудачный rebase или merge | `git rebase --abort` / `git merge --abort` |

### Подпись и Verified

```
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519_signing.pub
git config --global commit.gpgsign true
git log --show-signature -1            # проверить подпись последнего коммита
```

Ключ добавляется в GitHub как **Signing Key** (отдельно от Authentication Key), email
автора должен быть подтверждённым адресом аккаунта. Unverified означает: коммит не
подписан, подписан другим ключом или email не совпадает. Исправление для неотправленных
коммитов — `git commit --amend -S --no-edit` (последний) или `git rebase -S origin/main`
(все коммиты ветки). Вернуть: `git config --global --unset commit.gpgsign`.

### Концы строк и служебные файлы

- На Windows `core.autocrlf=true`: в рабочей копии CRLF, в репозитории LF. Файлы
  `ci/**`, `.github/**`, `*.sh` всегда LF (`.gitattributes`).
- Все файлы показаны изменёнными без реальной правки — концы строк: проверить
  `git diff --stat` с `-c core.autocrlf=true`; после правки `.gitattributes` —
  `git add --renormalize .`.
- `fatal: Unable to create '…/.git/index.lock': File exists` — убедиться, что git не
  запущен (IDE, другой терминал), затем удалить `.git/index.lock`.

## Linux-стенд и Orange Pi

Подробно — [Linux-стенд](LINUX_STAND.md).

| Проблема | Решение |
| --- | --- |
| `ModuleNotFoundError: No module named 'tomllib'` или «needs Python 3.11+» | Запущен системный Python 3.8. В каждой новой оболочке: `. ~/.local/stm32-gdbtest/env.sh`, проверить `python3 --version` → 3.11.16 |
| Не знаю, всё ли установлено и доступно | `python3 -B -m stm32_gdbtest doctor [--stand <стенд>]` |
| `FAIL usb … no read/write access` | Правила udev (раздел «Доступ к USB» в [Linux-стенде](LINUX_STAND.md)), переподключить отладчик |
| `FAIL openocd … interface/stlink.cfg` | Найден OpenOCD 0.10 из apt: выполнить `env.sh`, чтобы первым в `PATH` был xPack OpenOCD |
| J-Link STLink (Nucleo): `GDB server startup timed out`, в `jlink.log` подключение около 10 с | Окно условий J-Link STLink ждёт подтверждения. Один раз в графическом сеансе (монитор или удалённый рабочий стол): `JLinkExe -USB <serial>`, `connect`, отметить галочку. Запасной вариант — `startup_timeout_s = 30` в стенде |
| Сбой загрузки при установке окружения (например, HTTP 500 от GitHub) | Сценарий сам повторяет загрузку и `git fetch` до 4 раз с паузами 15, 30, 60 с; если не помогло — запустить `python3 tools/linux_stand.py install` ещё раз: установленное пропускается. В CI — перезапустить упавшее задание (Re-run failed jobs); загрузки кэшируются |
| Переставить один компонент | `rm -rf ~/.local/stm32-gdbtest/<каталог компонента>` и `python3 tools/linux_stand.py install --only <имя>` |

Вернуть систему в исходное состояние:

```sh
rm -rf ~/.local/stm32-gdbtest                     # окружение стенда целиком
sudo rm /etc/udev/rules.d/60-openocd.rules        # правила udev ST-Link
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo dpkg -r jlink                                # ПО J-Link
rm -rf /tmp/stm32-gdbtest-locks                   # только если нет запущенных runner
```

## Аппаратные запуски

| Сообщение | Что делать |
| --- | --- |
| `Debugger already owned by another runner …` | Отладчик занят другим запуском (другой проект, CTest, второй терминал). Дождаться его окончания; параллельно один отладчик не использовать |
| `Abandoned debugger ownership …` | Прежний runner завершился аварийно. Проверить и остановить оставшиеся серверы, затем повторить запуск (см. ниже) |
| `GDB server exited before ready; see server.log` | Открыть `server.log` каталога запуска: неверный serial, отладчик занят чужой программой, нет доступа к USB |
| `GDB server startup timed out after N s` | Сервер не дошёл до готовности. Посмотреть `server.log` и журнал сервера; медленному отладчику — `startup_timeout_s` в стенде |
| Предупреждение `Flash capacity differs … image fits both` | Заводской размер Flash больше профиля (BluePill-Plus 128 KiB); запуск не прерывается |
| После опыта плата с другой прошивкой или с хвостом 0xA5 | `run_hw.py … --steps build full-ff` записывает прошивку CI с хвостом 0xFF |

Оставшиеся процессы серверов:

```sh
pgrep -a openocd; pgrep -a JLink                  # Linux
kill <pid>                                        # затем kill -9 <pid>, если не завершился
```

```powershell
Get-Process openocd, JLinkGDBServerCL, ST-LINK_gdbserver, arm-none-eabi-gdb* -ErrorAction SilentlyContinue
Stop-Process -Id <pid>
```

Каталог запуска указан в итоговой строке `run` и в `summary.json` сценария `run_hw.py`.
Там лежат `result.json`, `server.log`, `gdb.log`, `recovery.log`, журналы серверов и для
удалённого стенда `tunnel.log`
([API](API.md), [проверки и CI](testing.md)).

## Удалённый GDB-сервер по SSH

Настройка — [Linux-стенд](LINUX_STAND.md#удалённый-gdb-сервер-windows-или-wsl--orange-pi).
Проверка связи вручную с теми же ключевыми параметрами, что у runner:

```powershell
ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes -i <ключ> orangepi@<хост> "python3 --version"
```

| Сообщение | Что делать |
| --- | --- |
| `Permission denied (publickey…)` в `tunnel.log` | Ключ не добавлен в `~/.ssh/authorized_keys` на хосте стенда или указан другой `identity_file`; ключ с фразой-паролем — только через `ssh-agent` |
| `Host key verification failed` | Ключа хоста нет в `known_hosts` или он изменился (переустановка ОС): один раз `ssh orangepi@<хост> exit`; для изменившегося ключа сначала `ssh-keygen -R <хост>` |
| `Stand host refused the run: busy …` | Отладчик на хосте стенда занят: другой запуск с Windows или локальный запуск на Orange Pi |
| `Stand host refused the run: abandoned …` | Прежний запуск на хосте стенда завершился аварийно: на Orange Pi `pgrep -a openocd; pgrep -a JLink`, остановить остатки, повторить |
| `Stand host refused the run: executable …` | Сервер не найден на хосте стенда: проверить путь `executable`, для OpenOCD — наличие `~/.local/stm32-gdbtest/env.sh` или `env_script` |
| `GDB server exited before ready; see server.log and tunnel.log (env_script …)` | Код 97: указанный `env_script` не удалось подключить; код 255: ошибка SSH (ключ, хост, сеть) |
| `Stand host refused the run: port …` | Случайно выбранный порт сервера на хосте стенда занят: повторить запуск |
| `GDB server startup timed out after N s` для удалённого стенда | Предел — `startup_timeout_s` + 10 с на SSH; посмотреть `server.log` и `tunnel.log` |
| `Passwords are not supported in [remote]` | Пароли в стенде не допускаются: настроить вход по ключу |

Вернуть как было: удалить таблицу `[remote]` из стенда (или файл стенда), убрать ключ
из `~/.ssh/authorized_keys` на хосте стенда, запись хоста — `ssh-keygen -R <хост>`.

## Пакеты подготовленного запуска и аппаратный CI

Подробно — [аппаратный CI](HARDWARE_CI.md).

| Сообщение | Что делать |
| --- | --- |
| `Preparation failed, package not written: …` | Подготовка сценария дала ERROR: запустить `run --prepare-only` для него и разобрать `result.json` |
| `Package file changed: …`, `Package contents do not match its manifest` | Пакет повреждён или изменён после `pack`: создать заново, не править zip вручную |
| `The Tests directory must be inside the profile directory` | Каталог сценариев вынесен из профиля: перенести или собрать пакет из профиля |
| Сценарий на стенде не находит вспомогательный модуль | Добавить его при упаковке: `pack … --include helpers` |
| Задание `hardware` не стартует | Раннер не в сети или без метки `stm32-stand`: Settings → Actions → Runners |

Вернуть как было: удалить `build/ddtt-packages` и `build/packages`; раннер — раздел
«Установка раннера» в [аппаратном CI](HARDWARE_CI.md).

## Docker и CI

| Проблема | Решение |
| --- | --- |
| Docker Hub недоступен при сборке образа | `docker build --build-arg BASE_IMAGE=<зеркало>/ubuntu:24.04 …` ([проверки и CI](testing.md)) |
| Файлы в `build/` созданы root после запуска контейнера на Linux | Запускать с `--user "$(id -u):$(id -g)" -e HOME=/tmp`; удалить старые: `sudo rm -rf build tests/firmware/build` |
| CI красный, а локально всё проходит | Сравнить коммит проверки с последним коммитом ветки; открыть артефакт `offline-results` или `linux-stand-*` |

Удалить образ и кэш: `docker image rm stm32-gdbtest-ci:local`, `docker builder prune`.

## Для агентов

- Агент в облачной копии без доступа к GitHub передаёт коммиты владельцу через
  `git bundle` в `build/` рабочей копии владельца (в `.git` писать нельзя); там
  `git fetch <bundle> <ветка>:refs/agent/tmp`, `git cherry-pick -S` новых коммитов и
  `git update-ref -d refs/agent/tmp`. Bundle строится от коммита, который есть у
  владельца (например, от `origin/main`).
- Агент не выполняет push, не ставит теги и не записывает пароли; для SSH к стендам —
  только ключи.

## Не сравнивайте зарезервированные биты MMIO

F030 ADC CFGR2 в опыте читался как 0x1000 при CKMODE=0. Проверяйте документированное поле `ADC1->CFGR2 & ADC_CFGR2_CKMODE`, не весь регистр. Сверяйте маску с header/RM нужного MCU; не маскируйте неожиданный результат без анализа. [Протокол](F030_CMSIS_ADC_DMA.md).

Собственные профили/примеры и новые пакеты используют `tests`; чтение старых `Tests` сохранено. Локальные remote-стенды — `remote.toml` / `<profile>-remote.toml`, исключённые из Git. После переименования повторить configure. [Соглашения](maintenance.md).

## Build самостоятельного fixture

Ошибка «Output directories must remain inside the selected project root»: размещайте
build внутри каталога примера (tests/hal-f030/build/debug), а не общего build
репозитория модуля. Не отключайте защиту runner; исправьте binaryDir в preset.

## CMake cache при смене Windows и Linux

Не используйте один build попеременно из Windows и Linux-контейнера: CMakeCache
сохраняет абсолютные пути. Сообщение «current CMakeCache.txt directory is different»
возникает до проверки firmware и не означает её дефект. Сохраните отчёт ошибки и
старый build под другим именем внутри workspace, затем создайте чистый build
для текущей ОС. Для tests/hal-f030 CI использует build/ci-gcc13; сохранять нужно
именно этот каталог, не Git checkout и не весь каталог с аппаратными отчётами.
После успешного повторного HAL-этапа укажите два прогона, не единый 15/15 PASS.

## Не смешивать prepare и HW-отчёты одной сессии

CTest prepare и CLI run пишут result.json в session.out. Выполняйте их последовательно
или используйте отдельные сессии/out. Подсчёт всех новых result.json без фильтра
по mode/id может ошибочно связать prepare с аппаратным сценарием. При конфликте
сохраните отчёты и повторите полный набор отдельно; не объявляйте его PASS.
