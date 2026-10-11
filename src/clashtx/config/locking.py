from __future__ import annotations

import fcntl
import os
import threading
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

_LOCK = threading.RLock()
_LOCAL = threading.local()


@contextmanager
def file_lock(path: Path):
    """Reentrant in one thread; serialize threads and independent CLI processes."""
    with _LOCK:
        held = getattr(_LOCAL, 'held', {})
        _LOCAL.held = held
        key = str(path.resolve())
        if key in held:
            yield
            return
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            os.fchmod(fd, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX)
            held[key] = fd
            yield
        finally:
            held.pop(key, None)
            os.close(fd)


def config_transaction(function):
    @wraps(function)
    def wrapped(self, *args, **kwargs):
        with self.store.transaction():
            return function(self, *args, **kwargs)
    return wrapped
