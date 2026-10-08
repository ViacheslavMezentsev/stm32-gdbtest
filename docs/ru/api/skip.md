# skip

[API](index.md) · [English](../../en/api/skip.md)

`skip(reason) -> NoReturn`

Поддержка: Unreleased после 0.3.0; ТЗ API 0.3.9; API_VERSION=1.

Завершает неприменимый сценарий со статусом SKIP. reason — точный str, непустой после strip,
корректный Unicode; размер UTF-8 не больше api.records.max_text_bytes. Превышение даёт ApiError
limit_exceeded, неверная причина — invalid_arguments. Лимит не расходует бюджет records.

```python
target.record("capability", {"available": False})
if not target.records("capability")[-1]["data"]["available"]:
    target.skip("Optional interface is not configured")
```

records произвольны и принадлежат одному сценарию. skip не отключает другие сценарии;
для пропуска блока используйте if. Если проверяется исправность интерфейса, отказ связи — FAIL/ERROR.
Неизвестное состояние не превращать в SKIP.

Записи сохраняются при включённом capture, completion=interrupted; JSON содержит skip_reason,
JUnit — skipped/message. Код завершения77; CTest SKIP_RETURN_CODE=77. SKIP не PASS.
Ошибка capture оставляет исход SKIP, но код команды2 и отдельную ошибку инфраструктуры.
Ошибка teardown меняет исход на ERROR и сохраняет skip_reason.

Метод не возвращает управление: внутреннее исключение наследует BaseException, обычный
except Exception его не перехватывает; finally выполняется. Не перехватывайте BaseException.
Перехваченный skip при нормальном возврате сценария даёт ERROR. Неуспешные записанные checks
и активное исключение нельзя заменить SKIP. Ранее произвольно пойманные ошибки не отслеживаются.
Автоматического запрета после чтения/навигации нет; агент уже мог прошить/запустить MCU.
skip не отменяет действия. Не вызывайте его из finally для замены ошибки.

Миграция: обработчики кодов должны принимать77 отдельно от0/1/2; не использовать max для
приоритета исходов. Старые отчёты остаются читаемыми. `run_hw.py --allow-skip HW_ID` разрешает
конкретный пропуск; по умолчанию неожиданный SKIP не принимается. Счётчики skipped и passed
раздельны; все SKIP — nothing_tested. requires не поддерживается.

Проверки: [host](../../../tests/host/test_skip.py). Принятые границы практики —
[API_ACCEPTANCE](../API_ACCEPTANCE.md). Выпуск с методом ещё не опубликован.
