"""
RU: Нейтральное наблюдение: эталон, явная инъекция, проверенная очистка.
EN: Neutral live observation: oracle, explicit injection, verified cleanup.

Raw GDB accesses below are specific to this reserved SRAM/core-register layout;
they are not the public MMIO transport guarantee or a general peripheral recipe.
"""
import json, os, struct, sys
from pathlib import Path
from stm32_gdbtest import case


sys.path.insert(0, str(Path(__file__).parent))
from policy import layout, can_restore, fpb_supported, evidence
from fpb_adapter import Adapter, GdbTransport, JsonLog


# Core registers for the qualified IRQ0 experiment, not general-purpose MMIO.
VTOR = 0xe000ed08
ISER0 = 0xe000e100
ICER0 = 0xe000e180
ISPR0 = 0xe000e200
ICPR0 = 0xe000e280
IABR0 = 0xe000e300
FP_CTRL = 0xe0002000


# Exercise one bounded observation window and restore the owned state.
async def experiment(t, n, hooks=True, fail=False, passive=False, active=False, wrong=False,
                     fpb=False, vtor_hook=True, trampoline=False):
    import gdb
    inferior = gdb.selected_inferior()

    # Read one core register while stopped.
    def read(a):
        return struct.unpack('<I', inferior.read_memory(a, 4).tobytes())[0]

    # Write one qualified core register; no generic read-modify-write.
    def write(a, v):
        inferior.write_memory(a, struct.pack('<I', v))

    # Materialize a scalar now, never retain a lazy value across resume.
    def value(e):
        return int(gdb.parse_and_eval(e))
    bundle = Path(os.environ['LIVE_OBSERVER_BUNDLE'])
    symbols = json.loads((bundle / 'symbols.json').read_text())
    await t.reach('ready')
    base = value('&__observer_start')
    size = value('&__observer_end') - base
    loc = layout(base, size, value('sizeof(vectors)'))
    saved = inferior.read_memory(base, size).tobytes()
    if len(saved) != size:
        raise RuntimeError('incomplete SRAM snapshot')
    flash = inferior.read_memory(0x8000000, 4096).tobytes()
    vtor = read(VTOR)
    enabled = read(ISER0) & 1
    can_restore(read(IABR0) & 1, read(ISPR0) & 1)
    if enabled:
        raise RuntimeError('IRQ already owned')
    original = value('work')
    try:
        fpb_ctrl = read(FP_CTRL)
    except gdb.MemoryError:
        fpb_ctrl = None
    remap = fpb_ctrl is not None and fpb_supported(fpb_ctrl)
    t.record('capability', {'fpb_ctrl': fpb_ctrl, 'remap': 'AVAILABLE_UNTESTED' if remap else 'NOT_SUPPORTED'})
    adapter = Adapter(GdbTransport(), JsonLog(bundle / 'fpb-events.jsonl')) if fpb else None
    cleanup = {'status': 'ERROR'}
    try:
        if hooks:
            blob = bytearray((bundle / 'hook.bin').read_bytes())

            # Patch only the known wrapper literals from ELF symbols.
            for name, expr in [('irq_original', '&original_irq'), ('function_original', '&original_work')]:
                struct.pack_into('<I', blob, symbols[name] - base, value(expr) | 1)
            struct.pack_into('<I', blob, symbols['continuation'] - base, value('&original_work') + 4 | 1)
            inferior.write_memory(base, bytes([165]) * size)
            inferior.write_memory(base, blob)
            write(loc['counters'], 0)
            write(loc['counters'] + 4, 0)
            vec = bytearray(inferior.read_memory(vtor, 512).tobytes())
            struct.pack_into('<I', vec, 64, symbols['irq_hook'] | 1)
            inferior.write_memory(loc['vectors'], vec)
            if vtor_hook:
                write(VTOR, loc['vectors'])
            if fpb:
                entry = value('&original_work') & ~1
                if inferior.read_memory(entry, 4).tobytes() != bytes.fromhex('80b483b0'):
                    raise RuntimeError('prologue changed')
                adapter.install((base, 1024), base + 768, symbols['fpb_hook'], target=entry)
            elif vtor_hook:
                t.write('work', symbols['fpb_hook' if trampoline else 'function_hook'] | 1)

            # A failed precondition must abort before resume, not merely accumulate FAIL.
            if read(VTOR) != (loc['vectors'] if vtor_hook else vtor):
                raise RuntimeError('VTOR installation readback')
            t.check('VTOR installed', read(VTOR), loc['vectors'] if vtor_hook else vtor)
        write(ISER0, 1)
        t.write('requested', n)
        if fail:
            raise ValueError('intentional before resume')
        if not passive:
            t.breakpoint('original_irq' if active else 'finished', temporary=True)
        t.resume(sync=False)
        stopped = await t.wait(timeout=0.2 if passive else 3)
        if passive:
            t.check('passive window', stopped['outcome'], 'timeout')
            await t.halt(timeout=2)
        else:
            t.check('window boundary', stopped['outcome'], 'stopped')
        if not passive and stopped['outcome'] != 'stopped':
            raise RuntimeError('window did not complete')
        if active:
            raise ValueError('intentional active ISR')

        # Collect facts once, then assess them against the independent host oracle.
        actual = value('delivered')
        calls = value('calls')
        t.check('original ISR', actual, n)
        t.check('original function', calls, n)
        t.check('result ABI', value('checksum'), sum((i * 3 + 1 for i in range(n))))
        if hooks:
            irq = read(loc['counters'])
            func = read(loc['counters'] + 4)
            t.record('evidence', {'expected': n, 'original_irq': actual, 'observed_irq': irq,
                                  'original_calls': calls, 'observed_calls': func, 'status': evidence(n, calls, func),
                                  'function_route': 'FPB remap' if fpb else 'direct SRAM wrapper, not FPB'})
            t.check('ISR count', irq, (n + 1 if wrong else n) if vtor_hook else 0)
            t.check('function count', func, n)
    finally:
        # Never restore executable SRAM until the known ISR has exited.
        await t.halt(timeout=2)
        steps = 0

        # Only this known ISR may be drained, with a bounded instruction count.
        while read(IABR0) & 1:
            pc = value('$pc') & ~1
            in_hook = base <= pc < base + len((bundle / 'hook.bin').read_bytes())
            in_original = (value('&original_irq') & ~1) <= pc < (value('&fault') & ~1)
            allowed = in_hook or in_original
            if not allowed or steps >= 32:
                raise RuntimeError('active unknown ISR; retain SRAM/VTOR')
            await t.step(unit='instruction')
            steps += 1
        can_restore(read(IABR0) & 1, 0)
        write(ICER0, 1)
        write(ICPR0, 1)
        can_restore(read(IABR0) & 1, read(ISPR0) & 1)
        if adapter and adapter.remove() not in ('VERIFIED', 'NOT_NEEDED'):
            raise RuntimeError('FPB cleanup blocked; retain SRAM')
        if hooks:
            # Guard areas must remain intact before saved bytes are restored.
            for start, end in ((base + 832, base + 1024), (base + 1032, base + 2048), (base + 2560, base + size)):
                if inferior.read_memory(start, end - start).tobytes() != bytes([165]) * (end - start):
                    raise RuntimeError('observer guard corrupted')
        write(VTOR, vtor)
        t.write('work', original)
        if read(VTOR) != vtor:
            raise RuntimeError('VTOR readback')
        inferior.write_memory(base, saved)
        if inferior.read_memory(base, size).tobytes() != saved:
            raise RuntimeError('SRAM readback')
        if inferior.read_memory(0x8000000, 4096).tobytes() != flash:
            raise RuntimeError('Flash changed')
        if read(ISER0) & 1:
            raise RuntimeError('IRQ remains enabled')
        cleanup.update(fpb=adapter.removal if adapter else 'NOT_USED', status='VERIFIED', drain_steps=steps,
                       sram=True, flash=True, vtor=True, irq_disabled=True)
        t.record('observer_cleanup', cleanup)

    # Repeat the original route in the same instance after verified removal.
    t.write('release', 1)
    t.breakpoint('ready', temporary=True)
    t.resume(sync=False)
    if (await t.wait(timeout=3))['outcome'] != 'stopped':
        raise RuntimeError('ready timeout')
    before_irq = value('delivered')
    before_calls = value('calls')
    t.write('requested', 3)
    write(ISER0, 1)
    try:
        t.breakpoint('finished', temporary=True)
        t.resume(sync=False)
        t.check('repeat after removal', (await t.wait(timeout=3))['outcome'], 'stopped')
        t.check('ISR after removal', value('delivered') - before_irq, 3)
        t.check('function after removal', value('calls') - before_calls, 3)
        t.check('SRAM after original repeat', inferior.read_memory(base, size).tobytes() == saved, True)
    finally:
        await t.halt(timeout=2)
        write(ICER0, 1)
        write(ICPR0, 1)


# Baseline without any observer.
@case('HW_OBSERVER_BASELINE', timeout_s=20)
async def baseline(t):
    await experiment(t, 7, hooks=False)


# Seven observed entries, checked against the independent oracle.
@case('HW_OBSERVER_SEVEN', timeout_s=20)
async def seven(t):
    await experiment(t, 7)


# A completed empty window is a valid zero.
@case('HW_OBSERVER_ZERO', timeout_s=20)
async def zero(t):
    await experiment(t, 0)


# Exercise cleanup after an exception before resume.
@case('HW_OBSERVER_EXCEPTION', timeout_s=20)
async def exception(t):
    await experiment(t, 7, fail=True)


# Wait passively, then halt explicitly.
@case('HW_OBSERVER_HALT', timeout_s=20)
async def halt_window(t):
    await experiment(t, 7, passive=True)


# Drain a known active ISR before removing its code.
@case('HW_OBSERVER_ACTIVE', timeout_s=20)
async def active_isr(t):
    await experiment(t, 7, active=True)


# Prove that a wrong expected count yields FAIL.
@case('HW_OBSERVER_NEGATIVE', timeout_s=20)
async def negative(t):
    await experiment(t, 7, wrong=True)


# Hardware FPB remap with a completed zero-event window.
@case('HW_OBSERVER_FPB_ZERO', timeout_s=20)
async def fpb_zero(t):
    await experiment(t, 0, fpb=True, vtor_hook=False)


# Hardware FPB remap observing seven function entries.
@case('HW_OBSERVER_FPB_SEVEN', timeout_s=20)
async def fpb_seven(t):
    await experiment(t, 7, fpb=True, vtor_hook=False)


# Observe both ISR and function without changing the original results.
@case('HW_OBSERVER_COMBINED', timeout_s=20)
async def combined(t):
    await experiment(t, 7, fpb=True)


# Remove FPB even when the body raises before resume.
@case('HW_OBSERVER_FPB_EXCEPTION', timeout_s=20)
async def fpb_exception(t):
    await experiment(t, 7, fpb=True, fail=True)


# Test displaced instructions directly, without claiming FPB behavior.
@case('HW_OBSERVER_TRAMPOLINE', timeout_s=20)
async def trampoline_control(t):
    await experiment(t, 7, trampoline=True)
