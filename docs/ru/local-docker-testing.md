# Локальные проверки: Docker и аппаратный стенд

[Документация](index.md) · [Проверки и CI](testing.md) · [English](../en/local-docker-testing.md)

Практический порядок для Windows/PowerShell и Docker Desktop (Linux amd64).
Нормативные требования — [ТЗ, разделы 9.3–9.5](../TECHNICAL_SPECIFICATION.md).
Linux-контейнер выполняет проверки до GDB-сервера; L6 выполняется отдельно на
согласованном Windows/Linux-стенде. Контейнер не заменяет нативную Windows-регрессию.

## Выбор прогона

| Задача | Команда в образе | Граница |
| --- | --- | --- |
| Окружение L0 | `python3 /opt/stm32-gdbtest-ci/verify.py` | Инструменты и закреплённые исходники, не поведение модуля |
| Документы L1 | `python3 ci/run_checks.py docs` | Включает strict ТЗ и фильтры публикации |
| Host L2/L3 | `python3 ci/run_checks.py host` | Подмены и CMake, без MCU |
| Полная offline-приёмка | `python3 ci/run_checks.py` | docs/format/host, все GCC × CMSIS-профили, HAL; L1–L5 |
| Аппаратная приёмка L6 | `run_hw.py` и `run_suite.py` на стенде | Только выбранные MCU/backend/прошивка |

Для коротких проверок допустим bind mount из [testing](testing.md).
Для полной матрицы на Windows рекомендуются **исходники и сборки в одном Docker volume**:
иначе чтение исходников через Windows остаётся узким местом. Этот приём заимствован
из [практики stm32-cmake-yml](https://github.com/ViacheslavMezentsev/stm32-cmake-yml/blob/main/docs/ru/local-docker-testing.md).
Его коэффициенты ускорения не являются измерениями stm32-gdbtest. При медленном I/O
сначала проверяйте размещение файлов, а не увеличивайте таймауты сценариев.

## 1. Образ и L0

Сеть нужна при сборке образа, но не при offline-проверках. Закрепления находятся в
[lock-файле](../../ci/dependencies.lock.json), установка — в `ci/docker/install.py`.
SHA-256 архивов проверяется при установке; `verify.py` проверяет версии, GDB-Python,
коммиты и обязательные файлы зависимостей, но не пересчитывает исходные архивы.
Пакеты Ubuntu обновляемы: их список сохранён в `/opt/stm32-gdbtest-ci/packages.txt`.

Из корня репозитория:

```powershell
$runId = Get-Date -Format 'yyyyMMdd-HHmmss'
$runRoot = Join-Path $PWD.Path "build/local-checks-$runId"
$volume = "gdbtest-checks-$runId"
$exportContainer = "gdbtest-export-$runId"
New-Item -ItemType Directory -Force $runRoot | Out-Null
$image = 'stm32-gdbtest-ci:local'
# Build when image inputs changed or the image is absent.
docker build -f ci/docker/Dockerfile -t $image .
if ($LASTEXITCODE -ne 0) { throw 'Image build failed' }
$imageId = docker image inspect --format '{{.Id}}' $image
if ($LASTEXITCODE -ne 0) { throw 'Image inspection failed' }
docker image inspect $imageId > "$runRoot/image-inspect.json"
docker run --rm --network none $imageId 2>&1 | Tee-Object "$runRoot/L0.log"
if ($LASTEXITCODE -ne 0) { throw 'L0 failed' }
```

Готовый образ можно переиспользовать при неизменных Dockerfile, lock-файле,
install.py, entrypoint.sh и verify.py. Один тег этого не доказывает: сохраняйте
image ID и происхождение сборки, повторяйте L0 даже при попадании в кэш.
Выполняйте команды через сохранённый `$imageId`, чтобы смена тега не подменила образ.

## 2. Чистый снимок

Для приёмки используйте подписанный коммит с чистым публичным деревом. Игнорируемые
локальные исследования и стенды в архив не входят. Рецепт использует Git archive,
не копирует `.git` и подходит также для linked worktree. Он не переносит подмодули:
в этом репозитории SDK поставляет образ. Если добавятся gitlink, нужен отдельный рецепт.

```powershell
$state = git status --porcelain
if ($LASTEXITCODE -ne 0) { throw 'Git status failed' }
if ($state) { throw 'Commit reviewed changes before acceptance snapshot' }
$sha = git rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve HEAD' }
$sha | Set-Content "$runRoot/commit.txt"
git archive --format=tar --output="$runRoot/source.tar" $sha
if ($LASTEXITCODE -ne 0) { throw 'Snapshot failed' }
Get-FileHash "$runRoot/source.tar" -Algorithm SHA256 | Format-List | Out-File "$runRoot/source-sha256.txt"
docker volume create $volume
if ($LASTEXITCODE -ne 0) { throw 'Volume creation failed' }
docker run --rm --network none --mount "type=volume,source=$volume,target=/work" --mount "type=bind,source=$runRoot/source.tar,target=/snapshot.tar,readonly" $imageId sh -c 'mkdir -p /work/source && tar -xf /snapshot.tar -C /work/source'
if ($LASTEXITCODE -ne 0) { throw 'Snapshot extraction failed' }
```

Не выдавайте `git archive HEAD` за проверку незакоммиченных изменений. Для рабочего
эксперимента нужен отдельный снимок текущих файлов с перечнем и SHA-256, отметкой dirty
и запретом редактирования во время упаковки. Его результат не является приёмкой HEAD.
Новый volume исключает старые CMake cache и отчёты; Windows build не переносится в Linux.

## 3. Проверки и сохранение при ошибке

```powershell
docker run --rm --network none --mount "type=volume,source=$volume,target=/work" -w /work/source $imageId python3 ci/run_checks.py 2>&1 | Tee-Object "$runRoot/checks.log"
$checksExit = $LASTEXITCODE
# Export even after a failed check. Include sources and all partial build evidence.
docker run --name $exportContainer --network none --mount "type=volume,source=$volume,target=/work,readonly" $imageId tar -czf /tmp/results.tar.gz -C /work source
if ($LASTEXITCODE -ne 0) { throw 'Archive failed; retain volume and container' }
docker cp "${exportContainer}:/tmp/results.tar.gz" "$runRoot/results.tar.gz"
if ($LASTEXITCODE -ne 0) { throw 'Export failed; retain volume and container' }
Get-FileHash "$runRoot/results.tar.gz" -Algorithm SHA256 | Format-List | Out-File "$runRoot/results-sha256.txt"
if ($checksExit -ne 0) { throw "Checks failed: $checksExit; evidence retained" }
```

Для docs-only замените команду на `python3 ci/run_checks.py docs`; остальной рецепт тот же.
Проверяйте `source/build/ci/summary.json` внутри архива: exit code 0, все ожидаемые
записи, отсутствие FAIL и пропущенных сочетаний. Без `--gcc`/`--profile` runner берёт
всю матрицу lock-файла; HAL — отдельная проверка GCC13. Частичный запуск не является
полной приёмкой. Runner продолжает независимые проверки после ошибки и возвращает
общий отрицательный результат; отсутствие отчёта не означает успех.

Два вызова runner в одном дереве перезапишут `build/ci/summary.json` и могут столкнуться
в сборках. Запускайте последовательно либо в разных volume. Архивируйте после завершения
всех процессов. Удаляйте только созданные здесь контейнер и volume после проверки архива:
`docker rm $exportContainer`, затем `docker volume rm $volume`; общий prune не нужен.
Нативный Windows host запускается отдельно: `python -B -m unittest discover -s tests/host -v`.
Сохраняйте версии Python/CMake и количества PASS/SKIP/ERROR; Linux не проверяет Windows paths/processes.

## 4. L6: до подключения

1. Зафиксируйте MCU, плату, backend, отладчик, режим подключения, питание и согласованную
   прошивку восстановления. Серийные номера и локальные пути остаются в `*.local.toml`.
   Сверьте профиль с фактической платой, исключите конкурирующие GDB-серверы.
2. Сохраните SHA исходников, ELF, build manifest, версии toolchain/GDB/встроенного Python
   и сервера. Для пакета сохраните SHA пакета. Запустите `doctor` по
   [руководству стенда](LINUX_STAND.md); его PASS не означает доступности MCU.
3. Выполните offline prepare для проверяемой и восстановительной прошивок. Отсутствие
   контракта не означает его PASS. Linux manifest с абсолютными путями нельзя использовать
   как Windows-сборку; для переноса применяется штатный pack.
4. Задайте ожидаемые исходы и границы времени до запуска. Один probe принадлежит одному
   запуску. Mass erase, option bytes, shared mode и обновление probe не входят в этот порядок.

## 5. L6: запуск, recovery, восстановление

Полный набор существующей сессии с восстановлением (пути замените своими):

```powershell
$session = 'tests/firmware/build/f411ce/hwtest/session.json'
$restore = $session
$stand = 'tests/firmware/stands/f411ce-openocd.local.toml'
python -B tests/firmware/run_suite.py --session $session --restore-session $restore --stand $stand
if ($LASTEXITCODE -ne 0) { throw 'Offline preparation failed' }
# Only on the agreed stand; writes firmware. Restore may be a different approved session.
python -B tests/firmware/run_suite.py --session $session --restore-session $restore --stand $stand --execute --timeout-recovery
if ($LASTEXITCODE -ne 0) { throw 'Hardware suite failed; inspect reports and restoration' }
```

`--execute` включает MCU; без него summary может быть PASS при `hardware=false` — это не L6.
`run_suite.py` проверяет manifest/MCU, готовит обе сессии, а после начала HW пытается
восстановить прошивку в finally и выполнить BOOT/GPIO (либо BOOT/BLINK).
Обрыв питания или принудительное завершение процесса могут прервать finally:
в этом случае состояние платы неизвестно до отдельного подтверждённого восстановления.

Жизненный цикл runner проверяется отдельно через [run_hw.py](../../tests/firmware/run_hw.py):
запись/повтор, strict identity, full-image A5/FF, отрицательный verify-only, timeout/recovery.
Он не заменяет полный набор сценариев и сам не гарантирует возврат пользовательской
прошивки: организуйте отдельный restore в finally внешнего запуска и проверьте его отчёты.

Короткий timeout запуска GDB в run_hw.py — отдельная инфраструктурная проверка:
он не доказывает вход в тело сценария, в отличие от timeout в run_suite.py.

Ожидаемый ERROR принимается только при совпадении причины и фазы отказа, а не только
exit code 2. Например, timeout внутри сценария должен наступить после входа в сценарий, иметь признак
host recovery и завершиться последующим положительным GPIO. Ошибка подключения вместо
такого timeout — провал проверки. Сохраните первоначальный ERROR; повтор не стирает его.
Восстановление reset_run после timeout и возврат оговорённого ELF — разные действия.

## 6. Итог и границы свидетельства

Паспорт прогона связывает SHA/dirty, image ID либо версии стенда, хеши ELF/manifest/пакета,
ожидаемые сценарии и фактические отчёты, исходы, длительности, SKIP, recovery и restore.
Общий PASS требует полного выбранного набора и подтверждённого восстановления; отсутствующий
отчёт, неподходящий MCU, отмена или неизвестное состояние платы не дают HW PASS.
При сбое сохраняйте JSON/JUnit, GDB/server/host logs и первоначальную причину до нового запуска.

Сырые журналы и персональная конфигурация остаются в игнорируемом build/локальной папке.
Публикуются обезличенные принятые результаты, без ссылок на недоступные локальные файлы.
Пример завершённой кампании — [приёмка rc.1](RC020_READINESS.md); новый рецепт volume
сам по себе не расширяет её аппаратное покрытие. В этом изменении повторяется только
проверка документации и smoke рецепта Docker, новые аппаратные опыты не заявляются.
