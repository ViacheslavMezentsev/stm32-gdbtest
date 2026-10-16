# Existing STM32 peripherals and custom models

[Русский](peripherals.md). Resolve tests/docs/tools from the module root and
platforms/scripts from the installed Renode distribution. Check the actual version.

## Start with an existing model

Renode 1.17 ships `platforms/cpus/stm32f103.repl`, `stm32f4.repl`, `stm32f429.repl`
and `scripts/single-node/stm32f103.resc`, `stm32f4_discovery.resc`.
These are starting points, not claims of complete MCU modeling.

| Location | Example REPL types |
| --- | --- |
| stm32f103.repl | UART.STM32_UART, GPIOPort.STM32F1GPIOPort, Timers.STM32_Timer, I2C.STM32F1_I2C, DMA.STM32G0DMA, IRQControllers.NVIC |
| stm32f4.repl | UART.STM32_UART, MTD.STM32F4_FlashController |
| stm32f429.repl | inherits stm32f4.repl and adds Video.STM32LTDC |

Read addresses, parameters, IRQ and DMARequest wiring in REPL, then the class source
and tests for the installed version. STM32G0DMA appearing in the F103 platform illustrates
why class names alone cannot establish compatibility. Compare required registers/modes
with target documentation; verify ADC, DMA, RCC and Flash separately. Do not copy large
MappedMemory windows into a physical MCU profile.

Monitor commands for a prepared local REPL/ELF:

```text
mach create
machine LoadPlatformDescription @path/to/local-platform.repl
sysbus LoadELF @path/to/firmware.elf
machine StartGdbServer 3333
```

The port must be free and owned by your run. Prefer tools/renode_probe.py for automated
experiments: owned processes, dynamic port, deadline, logs and cleanup. See
 docs/en/RENODE_PROBES.md for invocation.

Bundled resc may download a demo ELF. REPL may contain `ApplySVD @https://...` in init.
For offline use, prepare local dependencies, replace links in your copy and retain
provenance/hashes. Do not modify the installation. An experiment without SVD tags is
acceptable if explicitly identified; it does not test SVD loading. Loading three 1.17
platforms with unavailable SVD downloads produced log ERROR despite exit code 0.
Do not treat the process code as sufficient PASS. Copies without remote ApplySVD loaded,
but this only checks platform creation, not firmware execution or peripheral acceptance.

## When to build a model

Our published example is tests/renode-cache/platform.repl and flash_model.py:
a PythonPeripheral teaching Flash-cache controller. test_model.py checks it on the host;
run.py exercises it through GDB/Renode. It is not an accurate STM32 Flash model.
The neutral Cortex-M3 in tests/renode-startup has no ADC/DMA.

For a small register model use PythonPeripheral: separate file, explicit window size,
request.IsInit/IsRead/IsWrite and Offset/Length/Value; set request.Value on reads.
Update state and logs inside callbacks without GDB reads for logging. Start with host
tests using synthetic requests, then ELF/GDB. Do not assume callback length is always 4;
check unsupported widths explicitly. Consider C# and Register Framework for interrupts,
time and complex wiring. See the [official modeling guide](https://renode.readthedocs.io/en/latest/advanced/writing-peripherals.html).

## SVD, behavior and width

SVD tags do not create device behavior. A teaching SVD must match REPL and callbacks;
define effect oracles independently of the SVD generator/parser. Test incorrect
access/readAction and explicit description overrides separately. The 0.5.0 candidate provides [SVD and mmio.read/write](../../../docs/en/api/mmio.md); the internal parser does not replace an independent model oracle.

Renode width translation can split accesses and introduce RMW; inspect supported
interfaces and AllowedTranslation. Unsupported addresses/widths may produce a warning
and zero instead of a hardware fault. Logs are essential. For access counting and
subsequent board validation use [MMIO](mmio.en.md).

Evidence boundary: model → tested operation → independent criterion → original
PASS/FAIL/ERROR → limitations → repeat on an authorized board. A class being available,
a REPL loading or a UART banner does not establish DMA/ADC/Flash behavior.
