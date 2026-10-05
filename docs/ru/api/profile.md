# profile

[API](index.md) · [English](../../en/api/profile.md)

`profile: Profile` — отображение `target.toml` только для чтения с разделами прогона

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | индексация: 0.1.0rc1 / v0.1.0-rc.1; разделы, `get`, `origin`, `to_dict`: 0.3.0.dev0 (ядро) |
| Контракт принят в ТЗ API | индексация: 0.1.0; разделы: 0.3.3 |
| API_VERSION | 1 (индексация сохраняет опубликованный контракт) |
| Заменяет | `config`, `config_props`, `settings`, `sources` (удалены в 0.3.0 без алиасов) |
| Основание | проверочная прошивка `tests/firmware`, сценарии `HW_CI_PROFILE`, `HW_CI_ADC_SERIES`, `HW_CI_RESET` |

## Назначение

Описывает прогон, в котором выполняется сценарий: цель, эффективные настройки API и параметры
сценария, политику образа, захваченные файлы, текущий case, стенд и используемый GDB.

## Контракт и ограничения

- `profile[key]`, итерация и `len` читают `target.toml` так же, как в 0.1 (`profile["flash_start"]`).
- Разделы: `target`, `api` (эффективный `api.toml` с defaults ядра для `records`, `frames`,
  `execute`), `user` (таблица `[user]` из `api.toml`), `image` (выбранная политика или `None`),
  `files` (`{роль: {reference, sha256}}` для `target`, `api`, `image`, `session`), `case` (`id`,
  `function`, `timeout_s`, `labels`, `contracts`), `stand` (`backend`, `server`, `speed_khz`, `flash`),
  `gdb` (`version`, `stop_details`, `value_history`, `type_is_signed`).
- `get(path, default=None)` читает путь через точку; путь без имени раздела читает `target.toml`.
- `origin(path)` сообщает источник значения: `{"state": "file", "file", "sha256"}`,
  `{"state": "default"}`, `{"state": "override", "variable"}` или `{"state": "run", "section"}`;
  отсутствующий путь даёт `KeyError`.
- `to_dict()` возвращает обычную JSON-совместимую копию для `record` и отчётов.

Все разделы и вложенные отображения только для чтения (`TypeError` при присваивании); массивы — tuple.
`gdb.stop_details` равен `None` до первой остановки, затем `True`, если этот GDB сообщает детали
остановки. `files[...]["reference"]` не обещает доступность пути на другом хосте.

## Пример

```python
count = target.profile.get("user.measurement.count", 10)
if target.profile.stand["backend"] == "jlink":
    target.check("J-Link reset command", target.profile.get("api.reset.command"), "monitor reset")
target.record("run", target.profile.to_dict())
```

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), ревизия 0.3.3, п. 4.14.1–4.14.6.
- [record](record.md), [reset](reset.md).
