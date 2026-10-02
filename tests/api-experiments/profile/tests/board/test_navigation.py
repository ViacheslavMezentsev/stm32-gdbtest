"""R2 consumer experiments. Trusted C expressions are deliberately unrestricted."""
import gdb
from stm32_gdbtest import case
from lab.session import Research
from lab.navigation import caller_is as frame_caller_is, self_branch


def lab(t):
    # OpenOCD enforces hardware insertion even for GDB's internal finish/next points.
    gdb.execute('monitor gdb_breakpoint_override hard')
    gdb.execute('monitor debug_level 3')
    gdb.execute('set breakpoint auto-hw on')
    gdb.execute('set displaced-stepping off')
    gdb.execute('set debug remote on')
    value = gdb.lookup_global_symbol('sample').value()
    return Research(t, (int(value.address), int(value.type.sizeof)))


def caller_is(name, depth=1):
    return frame_caller_is(gdb.newest_frame(), name, depth)


def continue_to(t, r, bp):
    number = bp.number
    r.last_stop = None
    gdb.execute('continue')
    stop = dict(r.last_stop or {})
    r.record('event_' + str(len(r.evidence)), stop)
    t.check('expected breakpoint event', number in stop.get('breakpoints', []), True)


@case('HW_R2_CONDITION', labels=('research', 'navigation'))
def condition(t):
    with lab(t) as r:
        bp = gdb.Breakpoint('process_sample', type=gdb.BP_HARDWARE_BREAKPOINT, temporary=True)
        r.owned.append(bp)
        bp.condition = 'sequence == 3 && input->mode == MODE_ACTIVE'
        continue_to(t, r, bp)
        t.check('condition verified after stop', int(gdb.parse_and_eval(bp.condition)) if bp.is_valid()
                else int(gdb.parse_and_eval('sequence == 3 && input->mode == MODE_ACTIVE')), 1)
        t.check('one-shot point deleted', bp.is_valid(), False)
        t.check('C expression from source', int(gdb.parse_and_eval('sequence + (uint32_t) input->mode')), 6)
        t.check('C sizeof', int(gdb.parse_and_eval('sizeof(input->bytes)')), 8)
        gdb.set_convenience_variable('result', gdb.Value(True))
        t.check('convenience boolean', bool(gdb.convenience_variable('result')), True)


@case('HW_R2_HITCOUNT', labels=('research', 'navigation'))
def hitcount(t):
    with lab(t) as r:
        bp = r.breakpoint('process_sample')
        bp.ignore_count = 2
        continue_to(t, r, bp)
        t.check('third natural call', int(gdb.parse_and_eval('sequence')), 2)
        t.check('three hits counted', bp.hit_count, 3)
        bp.delete()
        r.run_until('sum_bytes')
        t.check('immediate caller', caller_is('process_sample'), True)
        t.check('outer caller', caller_is('main', 2), True)
        t.check('wrong caller rejected', caller_is('main'), False)
        t.check('past stack end', caller_is('main', 20), False)
        # Built-in convenience function availability is independent of the frame-walk technique.
        try:
            result = bool(gdb.parse_and_eval('$_caller_is("process_sample")'))
            r.record('builtin_caller', {'available': True, 'value': result})
            t.check('builtin agrees', result, True)
        except gdb.error as exc:
            r.record('builtin_caller', {'available': False, 'reason': str(exc)})


@case('HW_R2_RETURN', labels=('research', 'navigation'))
def forced_return(t):
    with lab(t) as r:
        r.run_until('sum_bytes')
        t.check('caller before forced return', caller_is('process_sample'), True)
        t.force_return('100')
        t.check('forced return selected caller', gdb.newest_frame().name(), 'process_sample')
        r.run_until('process_sample')
        t.check('caller consumed replacement', int(gdb.parse_and_eval('checksum')), 100 ^ 0xffffff85)
        t.check('replacement changed natural result', int(gdb.parse_and_eval('checksum')) != (773 ^ 0xffffff85), True)


@case('HW_R2_FINISH', labels=('research', 'navigation'))
def finish(t):
    with lab(t) as r:
        r.run_until('sum_bytes')
        bp = gdb.FinishBreakpoint(gdb.newest_frame(), internal=True)
        r.owned.append(bp)
        continue_to(t, r, bp)
        t.check('natural return captured', int(bp.return_value), 773)
        t.check('finish selected caller', gdb.newest_frame().name(), 'process_sample')
        r.record('return_value', r.freeze(bp.return_value))
        r.run_until('process_sample')
        t.check('natural caller result', int(gdb.parse_and_eval('checksum')), 773 ^ 0xffffff85)


@case('HW_R2_STEP', labels=('research', 'navigation'))
def steps(t):
    with lab(t) as r:
        r.run_until('process_sample')
        before = int(gdb.newest_frame().pc())
        instruction = gdb.newest_frame().architecture().disassemble(before, count=1)[0]
        gdb.execute('stepi')
        t.check('single instruction advanced', int(gdb.newest_frame().pc()) != before, True)
        r.record('instruction', instruction)
        # Source stepping into the natural child call is bounded by an instruction-independent count.
        for _ in range(6):
            if gdb.newest_frame().name() == 'sum_bytes':
                break
            gdb.execute('step')
        t.check('step enters callee', gdb.newest_frame().name(), 'sum_bytes')
        gdb.execute('finish')
        t.check('CLI finish returns to caller', gdb.newest_frame().name(), 'process_sample')
        r.run_until('process_sample')
        for _ in range(6):
            if gdb.newest_frame().name() == 'main':
                break
            gdb.execute('next')
            t.check('next does not select child', gdb.newest_frame().name() != 'sum_bytes', True)
        t.check('next reaches outer caller', gdb.newest_frame().name(), 'main')


@case('HW_R2_WATCH', labels=('research', 'navigation'))
def watch(t):
    with lab(t) as r:
        for expression, access, expected_type in [('cycles', gdb.WP_WRITE, gdb.BP_HARDWARE_WATCHPOINT),
                                                 ('sample.bytes[0]', gdb.WP_READ, gdb.BP_READ_WATCHPOINT),
                                                 ('sample.bytes[1]', gdb.WP_ACCESS, gdb.BP_ACCESS_WATCHPOINT)]:
            bp = gdb.Breakpoint(expression, type=gdb.BP_WATCHPOINT, wp_class=access)
            r.owned.append(bp)
            t.check('hardware watchpoint selected', bp.type, expected_type)
            continue_to(t, r, bp)
            if access == gdb.WP_WRITE:
                t.check('first completed cycle write', int(gdb.parse_and_eval('cycles')), 1)
            else:
                t.check('read/access in sum_bytes', gdb.newest_frame().name(), 'sum_bytes')
            r.record('watch_' + str(access), dict(type=bp.type, expression=expression,
                                                 pc=int(gdb.newest_frame().pc())))
            bp.delete()


@case('HW_R2_CALL', labels=('research', 'navigation'))
def call(t):
    with lab(t) as r:
        r.run_until('process_sample')
        sp = int(gdb.newest_frame().read_register('sp'))
        pc = int(gdb.newest_frame().pc())
        before = r.read_memory(*r.ram)
        value = gdb.parse_and_eval('sum_bytes(sample.bytes, 8, 5)')
        t.check('direct call independent result', int(value), 775)
        t.check('stack restored', int(gdb.newest_frame().read_register('sp')), sp)
        t.check('PC restored', int(gdb.newest_frame().pc()), pc)
        t.check('input RAM preserved', r.read_memory(*r.ram).hex(), before.hex())
        r.record('direct_return', r.freeze(value))


@case('HW_R2_ASM', labels=('research', 'navigation'))
def assembly(t):
    with lab(t) as r:
        address = int(gdb.parse_and_eval('(unsigned int)Default_Handler')) & ~1
        bp = r.breakpoint('*' + hex(address))
        # Deliberately abandon application control flow; reset below is mandatory.
        gdb.execute('jump *' + hex(address))
        t.check('jump reached handler', int(gdb.newest_frame().pc()), address)
        bp.delete()
        frame = gdb.newest_frame()
        instruction = frame.architecture().disassemble(frame.pc(), count=1)[0]
        is_self_branch = self_branch(frame.pc(), instruction['asm'])
        gdb.set_convenience_variable('result', gdb.Value(is_self_branch))
        t.check('assembly self-branch', bool(gdb.convenience_variable('result')), True)
        raw = bytes(gdb.selected_inferior().read_memory(address, 2))
        t.check('Thumb b-to-self encoding', int.from_bytes(raw, 'little'), 0xe7fe)
        for _ in range(3):
            gdb.execute('stepi')
            t.check('PC stays in one-instruction loop', int(gdb.newest_frame().pc()), address)
        r.record('self_branch', instruction)
        t.boot(t.profile['reset_halt'])
        t.check('reset leaves loop', gdb.newest_frame().name(), 'main')
