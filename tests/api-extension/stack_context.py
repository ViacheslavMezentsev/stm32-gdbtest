"""E3 immutable stack/context snapshots; GDB events and explicit invalidation."""

from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class Frame:
    index: int
    kind: str
    function: object
    pc: int


@dataclass(frozen=True)
class Stack:
    frames: tuple
    complete: bool
    termination: str
    reason: object


@dataclass(frozen=True)
class Context:
    PC: int
    SP: int
    stack: Stack
    run_id: str
    stop_id: int
    revision: int

    def __getitem__(self, name):
        if name not in ('PC', 'SP', 'stack', 'run_id', 'stop_id', 'revision'):
            raise KeyError(name)
        return getattr(self, name)


class Contexts:
    def __init__(self, backend):
        self.backend = backend
        self.run_id = uuid.uuid4().hex
        self.stop_id = 0
        self.revision = 0
        self.closed = False

    def invalidate(self, *, stopped=False):
        self.revision += 1
        if stopped:
            self.stop_id += 1

    def current(self, context):
        return (not self.closed and self.backend.stopped()
                and (context.run_id, context.stop_id, context.revision)
                == (self.run_id, self.stop_id, self.revision))

    def capture(self, *, max_frames=8):
        if type(max_frames) is not int or not 1 <= max_frames <= 64:
            raise ValueError('max_frames must be 1..64')
        if self.closed or not self.backend.stopped():
            raise RuntimeError('no live stopped context')
        top = self.backend.newest()
        if top is None:
            raise RuntimeError('no newest frame')
        # Mandatory top-frame registers: no fallback to selected older frame.
        pc, sp = self.backend.register(top, 'pc'), self.backend.register(top, 'sp')
        frames = []
        frame = top
        termination, reason = 'stack_end', None
        try:
            while frame is not None:
                if len(frames) == max_frames:
                    termination = 'depth_limit'
                    break
                frames.append(Frame(len(frames), self.backend.kind(frame),
                                    self.backend.name(frame), self.backend.pc(frame)))
                frame = self.backend.older(frame)
        except self.backend.errors as exc:
            termination, reason = 'unwind_error', str(exc)
        return Context(pc, sp, Stack(tuple(frames), termination == 'stack_end',
                                    termination, reason), self.run_id, self.stop_id, self.revision)

    def close(self):
        self.closed = True
        self.invalidate()


def caller_is(stack, name, *, depth=1):
    """Exact depth, counting every GDB frame. None means insufficient evidence."""
    if type(depth) is not int or depth < 1 or type(name) is not str or not name:
        raise ValueError('caller requires a nonempty name and depth >= 1')
    if depth >= len(stack.frames):
        return False if stack.complete else None
    actual = stack.frames[depth].function
    return None if actual is None else actual == name


def interrupted_frame(stack):
    """Consumer Cortex-M technique: skip up to four signal frames after handler."""
    index = 1
    for _ in range(4):
        if index >= len(stack.frames) or stack.frames[index].kind != 'signal':
            break
        index += 1
    if index >= len(stack.frames) or stack.frames[index].kind == 'signal':
        raise RuntimeError('interrupted frame unavailable: ' + stack.termination)
    return stack.frames[index]


class GdbFrames:
    def __init__(self):
        import gdb
        self.gdb = gdb
        self.errors = (gdb.error,)

    def stopped(self):
        thread = self.gdb.selected_thread()
        return thread is not None and thread.is_stopped()

    def newest(self):
        return self.gdb.newest_frame()

    def register(self, frame, name):
        return int(frame.read_register(name))

    def pc(self, frame):
        return int(frame.pc())

    def name(self, frame):
        return frame.name()

    def kind(self, frame):
        g = self.gdb
        return {g.NORMAL_FRAME:'normal', g.SIGTRAMP_FRAME:'signal',
                g.INLINE_FRAME:'inline', g.DUMMY_FRAME:'dummy'}.get(frame.type(), 'other')

    def older(self, frame):
        older = frame.older()
        if older is None:
            reason = frame.unwind_stop_reason()
            # This GDB build lacks FIRST_ERROR. Only OUTERMOST proves completeness.
            if reason != self.gdb.FRAME_UNWIND_OUTERMOST:
                raise self.gdb.error(self.gdb.frame_stop_reason_string(reason))
        return older


class GdbContexts(Contexts):
    """Close after each scenario. Raw monitor changes require explicit invalidate."""
    def __init__(self):
        backend = GdbFrames()
        super().__init__(backend)
        self.handlers = []
        try:
            for name in ('cont', 'stop', 'exited', 'new_objfile', 'memory_changed', 'register_changed'):
                registry = getattr(backend.gdb.events, name)
                def handler(event, stopped=(name == 'stop')):
                    self.invalidate(stopped=stopped)
                registry.connect(handler)
                self.handlers.append((registry, handler))
        except Exception:
            self.close()
            raise

    def close(self):
        for registry, handler in self.handlers:
            registry.disconnect(handler)
        self.handlers.clear()
        super().close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
