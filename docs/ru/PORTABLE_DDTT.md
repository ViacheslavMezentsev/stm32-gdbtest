# Переносимые отчёты DDTT

[Документация](index.md) · [English](../en/PORTABLE_DDTT.md)

Внешние инструменты P1 не меняют Target API. `ddtt_coverage.py` сохраняет прежний интерфейс;
необязательное поле карты `environment` выбирает hardware (по умолчанию), emulator или host.
Результаты других сред и purpose=manual исключаются. Это не реализация ручного режима runner.
Последняя автоматическая попытка выбранной среды определяет исход; ERROR/неполные данные — UNKNOWN.
На строке FAILED приоритетен, иначе UNKNOWN не позволяет записать зелёную DA. Комментарии запрещены.

## Кампания и перенос

Пример команд из корня потребителя (M — путь модуля):

```text
python M/examples/ddtt-coverage/bind_map.py --project . --elf build/app.elf --template hil/map.template.json --out build/map.json
python M/tools/ddtt_provenance.py begin --project . --revision FULL_SHA --map build/map.json --runs build/campaign/runs --out build/campaign/campaign.json --inputs src/app.cpp hil/test_app.py hil/map.template.json
# Run scenarios into the new runs directory; retain FAIL/ERROR.
python M/tools/ddtt_provenance.py seal --project . --runs build/campaign/runs --out build/campaign/campaign.json
python M/tools/ddtt_report.py --project . --map build/map.json --runs build/campaign/runs --campaign build/campaign/campaign.json --repository OWNER/REPO --out build/public-ddtt --annotations
```

Создайте build/campaign заранее. --inputs перечисляет все относящиеся к опыту отслеживаемые
файлы, включая конфигурацию/модель и сценарии. FULL_SHA — полный SHA проверяемой ревизии.
До begin нужна свежая сборка; сами снимки не доказывают, что произвольный переданный ELF
собран именно из этих исходников. Весь набор входов не должен редактироваться во время опыта.
Кампания связывает карту, входы до/после и хеши результатов, проверяет время и run.json.
Не превращайте старые результаты в новую подтверждённую кампанию задним числом.

Отчёт пересчитывается из результатов; его поля не берутся из непроверенного HTML. Публичный
комплект: index.html, public-data.json, lcov.info, coverage.xml, .nojekyll. Только разрешённые
поля, относительные пути и ссылки GitHub по SHA; произвольные actual/expected/records не включаются.
Сценарий открывается на первой строке либо на явной scenario_line карты. Разметку утверждает автор.
Это защита от случайно устаревших входов, не подписанная аттестация против намеренной подделки.

## Просмотр и CI

В VS Code откройте корень потребителя; локальный LCOV из ddtt_coverage.py содержит абсолютные
пути. Переносимый LCOV — относительные. HTML работает без сервера/CDN: выберите файл, нажмите
строку для проверок; доступны тёмная/светлая/авто темы. UNKNOWN отсутствует в числовом покрытии.
--annotations печатает workflow commands notice/error/warning с файлом/строкой; код успешного
экспорта 0 не заменяет вердикт сценария. Сценарий FAIL должен отдельно завершить CI ошибкой.

Публикуйте только public-ddtt как статический Pages artifact. На GitHub выберите Settings →
Pages → GitHub Actions, затем используйте отдельный ручной deploy workflow с pages:write и
id-token:write, только после успешных тестов. Его environment URL/Visit site открывает отчёт.
Автоматическая публикация и настройки аккаунта не входят в инструмент. Сайт репозитория может
уже иметь содержимое — не заменяйте его без поручения. Фрагменты для включения в свой workflow: [pages.yml](../../examples/ddtt-coverage/pages.yml); это не самостоятельный workflow.

Короткая проверка без платы — [Renode](RENODE_PROBES.md). Навык —
[coverage](../../skills/stm32-gdbtest-coverage/SKILL.md).
