"""Bounded I/O and cooperative output ownership for offline result tools."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile


class Budget:
    def __init__(self, limit, label):
        self.remaining = limit
        self.label = label

    def consume(self, size):
        if size > self.remaining:
            raise ValueError(self.label + ' size limit')
        self.remaining -= size


class Writer:
    def __init__(self, stream, budget):
        self.stream, self.budget = stream, budget

    def write(self, value):
        self.budget.consume(len(value.encode('utf-8')))
        return self.stream.write(value)


@contextmanager
def output_stream(path, budget):
    with Path(path).open('x', encoding='utf-8', newline='') as stream:
        yield Writer(stream, budget)


def write_json(path, value, budget):
    with output_stream(path, budget) as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')


@contextmanager
def ownership(output):
    """Serialize cooperating publishers; never remove another writer's lock."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    lock = output.with_name(output.name + '.lock')
    # All result commands use this lock. Uncooperative third-party writers are unsupported.
    stream = lock.open('x', encoding='ascii')
    try:
        with stream:
            stream.write(str(os.getpid()) + '\n')
        if output.exists() or output.is_symlink():
            raise FileExistsError(output)
        yield
    finally:
        lock.unlink()


def publish_json(path, value, budget):
    """Link a completed temporary file into place without replacing any destination."""
    path = Path(path)
    with ownership(path), tempfile.TemporaryDirectory(prefix='.results-', dir=path.parent) as directory:
        temporary = Path(directory) / 'report.json'
        write_json(temporary, value, budget)
        # A hard link publishes atomically and refuses an existing file on Windows and POSIX.
        # Unsupported filesystems fail explicitly; never fall back to a partial direct write.
        os.link(temporary, path)
