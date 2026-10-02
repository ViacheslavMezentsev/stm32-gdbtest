# Исследование GDB Python API для rc3

[Документация](../../../ru/index.md) · [English](../en/index.md)

Материалы одного исследования собраны здесь: исходный план, отчёты серий и
обезличенные результаты. Аппаратные опыты приостановлены 02.10.2026; отчёты фиксируют состояние
конкретных опытов, включая FAIL/ERROR. Это не утверждённое расширение публичного API.

- [Сводка R1–R18](summary.md) — все отчёты, результаты и границы доказанного.
- [API, техники и шаблоны](scenario-tools.md) — области применения, классификация и свойства API.
- [Именованный контекст исполнения](execution-context.md) — предложение контракта снимка.
- [Технический долг](technical-debt.md) — приостановленные этапы и открытые ограничения.
- [План исследования](plan.md) — обзор руководства GDB Python и программа экспериментов.
- L0: [GDB14](../results/rc3-gdb14-capabilities.json), [GDB16](../results/rc3-gdb16-capabilities.json).

| Серия | Отчёт | Результаты |
| --- | --- | --- |
| R1 | [Типизированные данные, кадры, RAM и отчёты](r1.md) | [JSON](../results/rc3-r1-results.json) |
| R2 | [Навигация, вызовы, watchpoints и ассемблер](r2.md) | [JSON](../results/rc3-r2-results.json) |
| R3 | [Команды точек, счётчики и запись прежнего значения](r3.md) | [JSON](../results/rc3-r3-results.json) |
| R4 | [Выходные буферы и подмена статуса](r4.md) | [JSON](../results/rc3-r4-results.json) |
| R5 | [Типы возврата и скрытый буфер структуры](r5.md) | [JSON](../results/rc3-r5-results.json) |
| R6 | [Отбор по стеку и рекурсивные кадры](r6.md) | [JSON](../results/rc3-r6-results.json) |
| R7 | [Диапазоны и бюджет watchpoints](r7.md) | [JSON](../results/rc3-r7-results.json) |
| R8 | [Бюджет точек по коду и резерв для finish](r8.md) | [JSON](../results/rc3-r8-results.json) |
| R9 | [Прерванные вызовы и подмена вложенного результата](r9.md) | [JSON](../results/rc3-r9-results.json) |
| R10 | [Fault и timeout незавершённого вызова](r10.md) | [JSON](../results/rc3-r10-results.json) |
| R11 | [Контекст IRQ и естественный возврат](r11.md) | [JSON](../results/rc3-r11-results.json) |
| R12 | [Запись DMA и наблюдение через watchpoints](r12.md) | [JSON](../results/rc3-r12-results.json) |
| R13 | [WFI, пробуждение и ход задержки](r13.md) | [JSON](../results/rc3-r13-results.json) |
| R14 | [Последовательности перехватов и порядок вызовов](r14.md) | [JSON](../results/rc3-r14-results.json) |
| R15 | [O2/Os, inline и доступность значений](r15.md) | [JSON](../results/rc3-r15-results.json) |
| R16 | [until, advance, nexti и причины остановки](r16.md) | [JSON](../results/rc3-r16-results.json) |
| R17 | [Скалярные типы и soft/hard-float ABI](r17.md) | [JSON](../results/rc3-r17-results.json) |
| R18 | [Структуры, HFA и методы C++](r18.md) | [JSON](../results/rc3-r18-results.json) |

[Consumer](../../../../tests/api-experiments/CMakeLists.txt) · [GDB probe](../../../../tools/research/gdb_api_probe.py)
