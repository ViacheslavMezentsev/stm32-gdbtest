# Схемы запуска

[Документация](index.md) → Схемы запуска · [English](../en/RUN_LAYOUTS.md)

Сценарий и отчёт одинаковы во всех схемах; меняется только файл локального стенда
(`*.local.toml`, `remote.toml`), который остаётся у пользователя.

| Схема | Где выполняются runner/GDB | Соединение |
| --- | --- | --- |
| Локальная | Windows или Linux | Локальный GDB-сервер и USB/SWD |
| Удалённый сервер | Windows/Linux, в том числе WSL2 | SSH к хосту стенда |
| Пакет | На хосте исполнения | Подготовленные входы, локальный или SSH-сервер |
| Hardware CI | Self-hosted хост стенда | Отдельная от сборки аппаратная задача |
| Эмулятор | Windows/Linux | Собственный Renode или QEMU, без платы |

Проверенный объём каждого маршрута — [матрица 0.5.0](../development/release-050-acceptance.md).
Наличие схемы не означает аппаратную приёмку любого ОС/backend/MCU.
[Renode](../guides/ru/RENODE.md), [QEMU](../guides/ru/QEMU.md).

### Локальный запуск: Windows или Linux

Runner, GDB-Python и сервер работают на одном компьютере. Это схема Windows
и Orange Pi; локальный Linux x86_64 пока не проверен на оборудовании.

```mermaid
---
config:
  look: classic
---
flowchart LR
    subgraph PC["Компьютер: Windows / Linux"]
        R["Runner + GDB-Python"] <--> S["GDB-сервер"]
        R --> O["Отчёт"]
    end
    S <-->|USB| D["Отладчик"]
    D <-->|SWD| M["STM32"]
```

### Удалённый сервер: Windows или WSL2 → Linux-стенд

Runner и сценарий работают на рабочем ПК; SSH запускает сервер на стенде
и передаёт соединение GDB через туннель. Отладчик физически подключён к стенду.

```mermaid
---
config:
  look: classic
---
flowchart LR
    R["Windows / WSL2: runner + GDB-Python"] <-->|SSH tunnel| S["Linux-стенд: GDB-сервер"]
    R --> O["Отчёт"]
    S <-->|USB| D["Отладчик"]
    D <-->|SWD| M["STM32"]
```

### Пакет: сборка отдельно от запуска

На компьютер стенда передаётся пакет с ELF, профилем и сценариями.
`run --package` запускает там и GDB-Python, и сервер; отчёты сохраняются там же.

```mermaid
---
config:
  look: classic
---
flowchart LR
    B["Windows / GitHub: сборка + pack"] --> P["Пакет"]
    P --> R["Linux-стенд: run --package + GDB-Python"]
    R --> O["Отчёт"]
    R <--> S["GDB-сервер"]
    S <-->|USB| D["Отладчик"]
    D <-->|SWD| M["STM32"]
```

### Аппаратный CI: GitHub и self-hosted раннер

GitHub-hosted job собирает и проверяет пакет без платы. Self-hosted job
на Orange Pi скачивает пакет, запускает аппаратную проверку и загружает отчёты.

```mermaid
---
config:
  look: classic
---
flowchart LR
    G["GitHub: build + prepare + pack"] --> A["Артефакт пакета"]
    A --> R["Orange Pi: self-hosted runner + GDB-Python"]
    R --> O["GitHub: отчёты"]
    R <--> S["GDB-сервер"]
    S <-->|USB| D["Отладчик"]
    D <-->|SWD| M["STM32"]
```

### WSL2 с USB-пробросом: аппаратно не проверено

Все процессы тестирования работают в WSL2; Windows передаёт USB-устройство
в Linux через usbipd-win. Это отдельный, пока не проверенный на платах вариант.

```mermaid
---
config:
  look: classic
---
flowchart LR
    W["WSL2: runner + GDB-Python + сервер"] <-->|usbipd-win| D["Отладчик: USB Windows"]
    W --> O["Отчёт"]
    D <-->|SWD| M["STM32"]
```

Удалённый режим работает только по ключам SSH; блокировка отладчика действует на
хосте стенда, связь контролируется сигналом присутствия. ST-LINK GDB Server на
Linux aarch64 недоступен (ST не выпускает его для arm64), поэтому на Orange Pi
используются OpenOCD, J-Link и st-util. Подробности: [Linux-стенд](../guides/ru/LINUX_STAND.md),
[GDB-серверы](../guides/ru/BACKENDS.md).

[Как читать метрики](HARDWARE_METRICS.md).
