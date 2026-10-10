# Локальный CI: порядок запуска и разбор результатов

[Документация](index.md) · [Проверки и CI](testing.md) · [English](../en/local-ci.md)

Практический порядок для Windows/PowerShell и Docker Desktop (Linux amd64).
Нормативные требования — [ТЗ, разделы 9.3–9.5](../TECHNICAL_SPECIFICATION.md).
Linux-контейнер выполняет проверки до GDB-сервера; L6 выполняется отдельно на
согласованном Windows/Linux-стенде. Контейнер не заменяет нативную Windows-регрессию.

## Сначала прочитайте это

Это единая инструкция для локальных проверок модуля, включая прежний local-docker-testing.
На Windows выполняйте шаги 1–3 ниже: **снимок → свежий Docker volume → проверки → архив**.
В volume должны находиться и исходники, и сборки. Bind mount нужен только для передачи
архива: не запускайте host/firmware/hal из рабочего каталога на NTFS или `/mnt/c`.
Не начинайте с пересборки образа, полной матрицы или увеличения таймаутов.

1. Выберите группу по изменению. Документы: `docs`; логика Python: `docs host`;
   C/C++: `format` и затронутая матрица; перед полной приёмкой — все группы.
2. Выберите ровно один снимок: чистый коммит или текущее рабочее дерево.
3. Переиспользуйте проверенный образ при неизменных входах, сохраните image ID и выполните L0.
4. Выполните выбранные проверки без сети; не меняйте снимок во время прогона.
5. Даже при ошибке экспортируйте свидетельства, проверьте summary и код процесса.
   Только затем удаляйте созданные контейнер/volume. GitHub CI итогового SHA остаётся обязательным.

## Выбор прогона

| Задача | Команда в образе | Граница |
| --- | --- | --- |
| Окружение L0 | `python3 /opt/stm32-gdbtest-ci/verify.py` | Инструменты и закреплённые исходники, не поведение модуля |
| Документы L1 | `python3 ci/run_checks.py docs` | Включает strict ТЗ и фильтры публикации |
| Host L2/L3 | `python3 ci/run_checks.py host` | Подмены и CMake, без MCU |
| Полная offline-приёмка | `python3 ci/run_checks.py` | docs/format/host, все GCC × CMSIS-профили, HAL; L1–L5 |
| Аппаратная приёмка L6 | `run_hw.py` и `run_suite.py` на стенде | Только выбранные MCU/backend/прошивка |

На Windows используйте volume даже для короткого выбранного набора.
Host-набор также выполняйте в volume: 10.10.2026 bind mount рабочего Windows-каталога
достиг лимита 600 с, а отдельный чистый снимок в volume прошёл за 26 с. Причина
разницы не изолирована до одного фактора; увеличивать лимит вместо переноса файлов не следует.
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
$runId = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$runRoot = Join-Path $PWD.Path "build/local-checks-$runId"
$volume = "gdbtest-checks-$runId"
$exportContainer = "gdbtest-export-$runId"
New-Item -ItemType Directory -Force $runRoot | Out-Null
$image = 'stm32-gdbtest-ci:local'
# Run only if the image is absent or its build inputs changed.
# docker build --platform linux/amd64 -f ci/docker/Dockerfile -t $image .
# if ($LASTEXITCODE -ne 0) { throw 'Image build failed' }
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

## 2. Снимок исходников

### Вариант A: чистый подписанный коммит

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
```

Не выдавайте `git archive HEAD` за проверку незакоммиченных изменений. Для рабочего
эксперимента нужен отдельный снимок текущих файлов с перечнем и SHA-256, отметкой dirty
и запретом редактирования во время упаковки. Его результат не является приёмкой HEAD.
Новый volume исключает старые CMake cache и отчёты; Windows build не переносится в Linux.

### Вариант B: рабочие изменения

Для проверки до коммита сохраните следующий фрагмент как `build/make-local-snapshot.py`.
Он берёт изменённые и новые неигнорируемые файлы, сохраняет удаления, хеши именно упакованных
байтов и dirty-статус. Не редактируйте дерево во время упаковки. Никакой `.git` в контейнер
не переносится; `docs.public` умеет проверять снимок без Git, `git init/add` не нужны.
Это проверка рабочего дерева, а не приёмка коммита из поля head.

```python
from pathlib import Path
import hashlib
import io
import json
import subprocess
import sys
import tarfile

root = Path.cwd()
out = Path(sys.argv[1]).resolve()
if not out.is_relative_to(root / "build"):
    raise SystemExit("Output must be in this checkout's ignored build directory")
out.mkdir(parents=True, exist_ok=True)
entries = subprocess.check_output(["git", "ls-files", "--stage", "-z"]).split(b"\0")
if any(entry.startswith(b"160000 ") for entry in entries):
    raise SystemExit("Gitlinks need an explicit submodule snapshot recipe")
names = subprocess.check_output([
    "git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"
]).decode("utf-8").split("\0")
manifest = {
    "kind": "working-tree",
    "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "status": subprocess.check_output(["git", "status", "--porcelain"], text=True),
    "files": {}
}
with tarfile.open(out / "source.tar", "w") as archive:
    for name in sorted(set(filter(None, names))):
        path = root / name
        if path.is_symlink():
            raise SystemExit("Symlinks need an explicit snapshot recipe: " + name)
        if not path.is_file():
            continue  # Preserve working-tree deletions.
        if path.resolve().is_relative_to(out):
            raise SystemExit("Snapshot output must be ignored by Git")
        data = path.read_bytes()
        manifest["files"][name] = hashlib.sha256(data).hexdigest()
        info = archive.gettarinfo(str(path), arcname=name)
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
manifest["archive_sha256"] = hashlib.sha256((out / "source.tar").read_bytes()).hexdigest()
(out / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
```

```powershell
python build/make-local-snapshot.py "$runRoot"
if ($LASTEXITCODE -ne 0) { throw 'Working-tree snapshot failed' }
```

### Общее для обоих вариантов: загрузка

```powershell
docker volume create $volume
if ($LASTEXITCODE -ne 0) { throw 'Volume creation failed' }
docker run --rm --network none --mount "type=volume,source=$volume,target=/work" --mount "type=bind,source=$runRoot/source.tar,target=/snapshot.tar,readonly" $imageId sh -c 'mkdir -p /work/source && tar -xf /snapshot.tar -C /work/source'
if ($LASTEXITCODE -ne 0) { throw 'Snapshot extraction failed' }
```

## 3. Проверки и сохранение при ошибке

```powershell
# Choose one set: @('docs'), @('docs', 'host'), or @() for all groups.
$checkArgs = @('docs', 'host')
docker run --rm --network none --mount "type=volume,source=$volume,target=/work" -w /work/source $imageId python3 ci/run_checks.py @checkArgs 2>&1 | Tee-Object "$runRoot/checks.log"
$checksExit = $LASTEXITCODE
$checksExit | Set-Content "$runRoot/checks-exit.txt"
# Export even after a failed check. Include sources and all partial build evidence.
docker run --name $exportContainer --network none --mount "type=volume,source=$volume,target=/work,readonly" $imageId tar -czf /tmp/results.tar.gz -C /work source
if ($LASTEXITCODE -ne 0) { throw 'Archive failed; retain volume and container' }
docker cp "${exportContainer}:/tmp/results.tar.gz" "$runRoot/results.tar.gz"
if ($LASTEXITCODE -ne 0) { throw 'Export failed; retain volume and container' }
Get-FileHash "$runRoot/results.tar.gz" -Algorithm SHA256 | Format-List | Out-File "$runRoot/results-sha256.txt"
if ($checksExit -ne 0) { throw "Checks failed: $checksExit; evidence retained" }
```

Полная матрица: `$checkArgs = @()`; документы: `@('docs')`; один профиль:
`@('firmware', '--gcc', '13.3.1-1.1', '--profile', 'f411ce')`.
Проверяйте `source/build/ci/<run>/summary.json` внутри архива: exit code 0, все ожидаемые
записи, отсутствие FAIL и пропущенных сочетаний. Без `--gcc`/`--profile` runner берёт
всю матрицу lock-файла; HAL — отдельная проверка GCC13. Частичный запуск не является
полной приёмкой. Runner продолжает независимые проверки после ошибки и возвращает
общий отрицательный результат; отсутствие отчёта не означает успех.

Каждый вызов runner создаёт `build/ci/<run>` и отдельные сборки `tests/<fixture>/build/ci/<run>`.
Для независимых снимков исходников по-прежнему используйте разные volume. Архивируйте после завершения
всех процессов. Удаляйте только созданные здесь контейнер и volume после проверки архива:
`docker rm $exportContainer`, затем `docker volume rm $volume`; общий prune не нужен.
Нативный Windows host запускается отдельно: `python -B -m unittest discover -s tests/host -v`.
Сохраняйте версии Python/CMake и количества PASS/SKIP/ERROR; Linux не проверяет Windows paths/processes.

## Время, зависания и параллельность

Основной выигрыш даёт размещение файлов, а не увеличение числа контейнеров.
В подготовке 0.4.1 на этой машине docs+host заняли около 39 с для host (451 тест,
4 штатных пропуска). Ранее другой снимок проходил за 26 с, а bind-прогон достиг 600 с.
Это наблюдения разных запусков, не контролируемый benchmark и не обещанный лимит.

- Начинайте последовательно. Один запуск `ci/run_checks.py` получает уникальные каталоги;
  независимые снимки требуют отдельных volume. Не копируйте новый снимок поверх старого:
  так удалённые файлы могут остаться внутри контейнера.
- `host.log` пополняется после завершения дочерней команды; пауза stdout не доказывает зависание.
  Посмотрите `docker ps`, `docker stats --no-stream` и в нужном контейнере
  `docker exec <container> ps -eo pid,etime,pcpu,stat,wchan:24,args`.
  Ожидание `p9_client_rpc` может указывать на доступ к Windows-файлам. Сначала проверьте mounts.
- Отдельно учитывайте сборку образа/загрузки, перенос архива, тесты и экспорт.
  Лимит внешнего процесса, таймаут subprocess в runner и ожидаемый HW timeout — разные вещи.
- При отмене сначала остановите именно свой выполняющийся контейнер через `docker stop <container>`.
  Сохраните частичные логи и volume; незавершённый запуск не PASS. Не делайте общий prune.
- Перенос только build в volume не устраняет чтение исходников с NTFS. Не сокращайте набор
  проверок и не ослабляйте таймауты, чтобы скрыть медленную файловую систему.

## Linux и нативные проверки

На Linux с checkout в собственной Linux-файловой системе bind mount допустим. В WSL
checkout на `/mnt/c`/`/mnt/d` остаётся Windows-файловой системой: используйте рецепт volume.
Для Bash после подготовки образа (запускайте из корня; это отдельная альтернатива PowerShell):

```sh
set -o pipefail
mkdir -p build
run_id="$(date -u +%Y%m%dT%H%M%S)-$$"
docker run --rm --network none --user "$(id -u):$(id -g)" -e HOME=/tmp \
  --mount "type=bind,source=$PWD,target=/workspace" \
  stm32-gdbtest-ci:local python3 ci/run_checks.py docs host 2>&1 | tee "build/local-$run_id.log"
check_exit=${PIPESTATUS[0]}
exit "$check_exit"
```

Без Docker: `python -B -m unittest discover -s tests/host -v`; для firmware:
`cmake --preset f411ce`, `cmake --build --preset f411ce`, `ctest --preset f411ce-offline`
из `tests/firmware` при заданных `ARM_TOOLCHAIN_ROOT` и `STM32CUBE_REPOSITORY`.
Нативные проверки не заменяют закреплённую Docker-матрицу. Linux-контейнер не подтверждает
Windows mutex, кодировки, пути или жизненный цикл Windows-процессов.
Полная матрица берётся из lock-файла: сейчас 3 GCC × 6 профилей, отдельно HAL GCC13.
`--gcc/--profile` не ограничивают HAL; `stand` не является аргументом run_checks.py —
это отдельная задача GitHub Offline. QEMU/Renode в приёмку этого модуля не входят.

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

Команда отдельного lifecycle-прогона (прошивка изменяется; restore организуйте отдельно):

```powershell
python -B tests/firmware/run_hw.py --profile f411ce --stand tests/firmware/stands/f411ce-openocd.local.toml
if ($LASTEXITCODE -ne 0) { throw 'Lifecycle check failed; retain reports and restore' }
```

Toolchain/Cube задаются `--toolchain`, `--cube` или `ARM_TOOLCHAIN_ROOT`, `STM32CUBE_REPOSITORY`;
на Linux — также env.sh стенда. Итог: `build/hw/<профиль>-<стенд>/<run>/summary.json`.

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

## Окружение

Образ `ci/docker/Dockerfile` собирается из закреплённого [lock-файла](../../ci/dependencies.lock.json):
Ubuntu 24.04 по digest, xPack GCC 13.3.1-1.1, 14.2.1-1.1, 15.2.1-1.1 (каждый с
`arm-none-eabi-gdb-py3`), CMake 3.28.3, Ninja 1.12.1, CMSIS из STM32CubeF0 1.11.6,
F1 1.8.7 и F4 1.28.3 (F1/F4 — только `Drivers/CMSIS`, F0 — также HAL) и `check_spec.py` навыка
embedded-tech-spec. Версии GCC и CMake совпадают с stm32-cmake-yml; CMake 3.19.8
не используется, так как модулю нужен CMake ≥ 3.25. Архивы проверяются по SHA-256,
репозитории — по коммиту. При сборке образ проверяет GDB-Python каждого GCC.


Если Docker Hub недоступен, можно задать `--build-arg BASE_IMAGE=<зеркало>/ubuntu:24.04`;
фиксируйте digest и происхождение замены. Не меняйте остальные зависимости ради обхода сети.

## HAL F030 в offline CI

Уровень `python -B ci/run_checks.py hal` собирает tests/hal-f030 на GCC13.3.1,
требует ровно24 CTest (22 prepare + trace + fixture), проверяет22 свежих JSON
с хешем ELF, без обращений к оборудованию. Контракты запрошенных сценариев — PASS;
для сценариев без contracts NOT_REQUESTED не означает проверку HAL.

Отдельный положительный preflight, затем пять независимых ошибок: отсутствующий
макрос, неверный macro context, return type HAL_ADC_Start_DMA, значение HAL_ERROR,
тип аргумента HAL_ADC_ConvCpltCallback. Каждый отказ должен иметь ERROR именно
в изменённом контракте. Сервер не запускается, прошивка MCU не выполняется.

Docker использует HAL F0 gitlink из прежнего закреплённого CubeF0 1.11.6;
F1/F4 остаются CMSIS-only. Workflow запускает `format host firmware hal` и сохраняет
каталог `tests/hal-f030/build/ci/<run>/` (логи, ELF, manifest, JSON/JUnit).
Каждая попытка CI получает новый каталог независимо от ОС.
Без аргументов runner также включает hal; --gcc/--profile ограничивают только
CMSIS-матрицу. Для HAL используйте ARM_TOOLCHAIN_ROOT GCC13, STM32CUBE_REPOSITORY;
без переменной берётся установленный GCC13 по умолчанию Windows/Linux.
HAL GCC14/15 и аппаратная регрессия остаются отдельными задачами.

Для приёмки rc.2 см. [матрицу](RC2_READINESS.md). `tests/firmware/run_hw.py`
использует boot/GPIO для проверки runner; полный набор F030 запускается отдельно.

## Docker и CI

| Проблема | Решение |
| --- | --- |
| Docker Hub недоступен при сборке образа | `docker build --build-arg BASE_IMAGE=<зеркало>/ubuntu:24.04 …` ([локальный CI](local-ci.md)) |
| Файлы в `build/` созданы root после запуска контейнера на Linux | Запускать с `--user "$(id -u):$(id -g)" -e HOME=/tmp`; старые артефакты сначала сохранить, затем исправить владельца только своего каталога сборки |
| CI красный, а локально всё проходит | Сравнить коммит проверки с последним коммитом ветки; открыть артефакт `offline-results` или `linux-stand-*` |
| Сборка образа: `PermissionError: … 'ninja'` в `verify.py` | Файл из zip-архива распакован без права на запуск (`zipfile` в Python не восстанавливает Unix-права). `install.py` восстанавливает их из архива; при своих правках распаковки проверять запуск `ninja --version` в собранном образе |
| `windows-host` красный, Linux зелёный: тест сравнивает пути | На Windows пути инструментов возвращаются с `\`. В тестах сравнивать пути в одном виде (`.replace("\\", "/")` или `Path`), а не строки как есть |
| `format`: clang-format нашёл отличия | Отформатировать изменённые C/H-файлы: `clang-format -i <файлы>` (версия — как в образе CI; локально проще в контейнере) и повторить `python3 ci/run_checks.py format` |
| Новый профиль сломал host-тест с эталонными данными | Тест перебирал все каталоги `profiles/`; эталон фиксирует свой список профилей, новый профиль добавляется в эталон отдельно |
| Нужен SDK производителя (Artery) вне CI | `python tools/vendor_sdk.py` ставит закреплённый архив туда, где его ищет CMake ([совместимые МК](COMPATIBLE_MCU.md)) |
| AT32 SDK установлен, но `run_hw.py` сообщает `AT32 SDK not found` | В `tests/firmware/build/hw-<профиль>-<стенд>/CMakeCache.txt` мог сохраниться прежний `AT32_SDK_ROOT`. Убедиться, что в выбранном каталоге есть `libraries/cmsis/cm4/device_support/at32f403a_407.h`; затем выполнить `cmake -S tests/firmware -B <каталог-сборки> -DAT32_SDK_ROOT=<каталог-SDK>` и заново весь `run_hw.py`. Результат после неуспешного build не засчитывать: старый `session.json` мог указывать на прежний ELF. Исходный FAIL сохранить. |
