# DDTT coverage examples

[Русское руководство](../../docs/ru/DDTT_COVERAGE.md) · [English guide](../../docs/en/DDTT_COVERAGE.md)

Templates reference the public [BluePill](https://github.com/ViacheslavMezentsev/stm32-hwtest-bluepill)
and [BlackPill](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill) firmware projects.
They contain reviewed source/check associations, not measured results or hardware configuration.
Use `bind_map.py` after building your ELF. Generated maps, evidence and LCOV belong in your ignored build directory.

Шаблоны связывают строки прошивки с проверками, но не содержат результатов или настроек стенда.
После сборки привяжите шаблон к ELF через `bind_map.py`. Не добавляйте сформированные карты и отчёты в Git.
