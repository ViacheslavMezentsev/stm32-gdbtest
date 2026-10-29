# profile

[API](index.md) · [English](../../en/api/profile.md)

**Доступен с:** 0.1.0-rc.1; разделы, `get`, `origin`, `snapshot` — 0.3.0 · **API 3 (0.5.0):** без изменений, `await` не нужен.

`profile: Profile` — отображение `target.toml` только для чтения с разделами прогона

## Назначение

Описывает прогон, в котором выполняется сценарий: цель, эффективные настройки API и параметры
сценария, политику образа, файлы данных проекта, захваченные файлы, сборку, текущий case, стенд и
используемый GDB.

## Контракт и ограничения

- `profile[key]`, итерация и `len` читают `target.toml` так же, как в 0.1 (`profile["flash_start"]`).
- Разделы: `target`, `api` (эффективный `api.toml` с defaults ядра для `records`, `frames`,
  `execute`), `user` (таблица `[user]` из `api.toml`), `image` (выбранная политика или `None`),
  `data` (файлы данных из `[data]` в `session.toml`, по имени: `data["board"]`),
  `files` (`{роль: {reference, sha256}}` для `target`, `api`, `image`, `session`, `data.<имя>`),
  `build` (сводка build manifest: `compilers`, `cube_packages`, `libraries`, `defines`, `sources`;
  `None` без манифеста), `case` (`id`,
  `function`, `timeout_s`, `labels`, `contracts`), `stand` (`backend`, `server`, `speed_khz`, `flash`, `reset_command`),
  `gdb` (`version`, `stop_details`, `value_history`, `type_is_signed`).
- `get(path, default=None)` читает путь через точку; путь без имени раздела читает `target.toml`.
- `origin(path)` сообщает источник значения: `{"state": "file", "file", "sha256"}`,
  `{"state": "default"}`, `{"state": "override", "variable"}` или `{"state": "run", "section"}`;
  отсутствующий путь даёт `KeyError`.
- `snapshot()` возвращает обычную JSON-совместимую копию всех разделов; `t.record(name, t.profile)`
  записывает такой снимок сам.

Все разделы и вложенные отображения только для чтения (`TypeError` при присваивании); массивы — tuple.
`gdb.stop_details` равен `None` до первой остановки, затем `True`, если этот GDB сообщает детали
остановки. `files[...]["reference"]` не обещает доступность пути на другом хосте.

Файл данных объявляется в `session.toml` и захватывается вместе с конфигурацией: прогон читает его
один раз, пакет переносит его в капсуле, а `origin()` указывает файл и SHA-256. Поддерживается TOML;
имя — строчные латинские буквы, цифры и `_`; объявленный, но отсутствующий файл — ошибка до подключения
к MCU.

```toml
# session.toml
[config]
target = "target.toml"
api = "api.toml"

[data]
board = "board.toml"
```

`build.libraries` собирается из макросов версий в исходниках (`__STM32F4xx_HAL_VERSION_*` →
`{"STM32F4xx_HAL": "1.8.3"}`): это объявленные версии, а не проверка совместимости API. `build.defines`
— ключи `-D` модулей сборки, по ним видно, собрана ли прошивка с HAL (`USE_HAL_DRIVER`) или LL
(`USE_FULL_LL_DRIVER`).

## Пример

```python
count = t.profile.get("user.measurement.count", 10)
if t.profile.stand["backend"] == "jlink":
    t.check("J-Link reset command", t.profile.stand["reset_command"], "monitor reset")
led = t.profile.data["board"]["board"]["led"]          # "PA5" из board.toml
t.check("CMSIS-only firmware", "USE_HAL_DRIVER" in t.profile.build["defines"], False)
t.record("run", t.profile)
```

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), п. 4.14.1–4.14.8.
- [record](record.md), [reset](reset.md).

С v0.4.0 `stand.backend` также принимает `st-util`; его настройка описана в [backend](../../guides/ru/BACKENDS.md#st-util-v040).
