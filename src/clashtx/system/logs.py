from __future__ import annotations

import os
from pathlib import Path

from clashtx.config.locking import file_lock

DEFAULT_MAX_BYTES = 20 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 3
DEFAULT_KEEP_BYTES = 5 * 1024 * 1024
CHUNK_BYTES = 64 * 1024


def _lock(log_file: Path):
    return file_lock(log_file.parent / '.logs.lock')


def _limit_file(path: Path, limit: int) -> None:
    if not path.exists() or path.stat().st_size <= limit:
        return
    fd = os.open(path, os.O_RDWR)
    try:
        size = os.fstat(fd).st_size
        offset = 0
        while offset < limit:
            block = os.pread(fd, min(CHUNK_BYTES, limit - offset), size - limit + offset)
            if not block:
                break
            written = 0
            while written < len(block):
                amount = os.pwrite(fd, block[written:], offset + written)
                if amount <= 0:
                    raise OSError("Unable to compact log.")
                written += amount
            offset += len(block)
    finally:
        # In-place compaction needs no second full-sized file on a full disk.
        try:
            os.ftruncate(fd, limit)
        finally:
            os.close(fd)


def _rotate(log_file: Path, backup_count: int) -> None:
    log_file.with_name(f'{log_file.name}.{backup_count}').unlink(missing_ok=True)
    for index in range(backup_count - 1, 0, -1):
        source = log_file.with_name(f'{log_file.name}.{index}')
        if source.exists():
            source.replace(log_file.with_name(f'{log_file.name}.{index + 1}'))
    if log_file.exists():
        log_file.replace(log_file.with_name(f'{log_file.name}.1'))


class BoundedLog:
    """The only writer: rotate before writes, never depend on a UI polling timer."""
    def __init__(self, log_file: Path, *, max_bytes: int = DEFAULT_MAX_BYTES, backup_count: int = DEFAULT_BACKUP_COUNT):
        if max_bytes < 1 or backup_count < 1:
            raise ValueError('Log limits must be positive.')
        self.path, self.max_bytes, self.backup_count = log_file, max_bytes, backup_count
        self.dropped_bytes = 0
        self.normalize()

    def normalize(self) -> None:
        try:
            with _lock(self.path):
                _limit_file(self.path, self.max_bytes)
                for backup in self.path.parent.glob(self.path.name + '.*'):
                    suffix = backup.name[len(self.path.name) + 1:]
                    if suffix.isdigit():
                        if not 1 <= int(suffix) <= self.backup_count:
                            backup.unlink(missing_ok=True)
                        else:
                            _limit_file(backup, self.max_bytes)
        except OSError:
            pass  # Drain core output even when storage is temporarily unavailable.

    def write(self, data: bytes) -> None:
        try:
            with _lock(self.path):
                offset = 0
                while offset < len(data):
                    size = self.path.stat().st_size if self.path.exists() else 0
                    if size >= self.max_bytes:
                        _rotate(self.path, self.backup_count)
                        size = 0
                    amount = min(len(data) - offset, self.max_bytes - size, CHUNK_BYTES)
                    fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
                    with os.fdopen(fd, 'wb') as output:
                        os.fchmod(output.fileno(), 0o600)
                        output.write(memoryview(data)[offset:offset + amount])
                    offset += amount
        except OSError:
            self.dropped_bytes += len(data) - offset if 'offset' in locals() else len(data)


def rotate_log(log_file: Path, *, max_bytes: int = DEFAULT_MAX_BYTES, backup_count: int = DEFAULT_BACKUP_COUNT) -> bool:
    with _lock(log_file):
        if not log_file.exists() or log_file.stat().st_size <= max_bytes:
            return False
        _limit_file(log_file, max_bytes)
        _rotate(log_file, max(1, backup_count))
        return True


def trim_log(log_file: Path, *, max_bytes: int = DEFAULT_MAX_BYTES, keep_bytes: int = DEFAULT_KEEP_BYTES) -> int:
    with _lock(log_file):
        if not log_file.exists():
            return 0
        size = log_file.stat().st_size
        if size <= max_bytes:
            return 0
        _limit_file(log_file, max(1, min(keep_bytes, max_bytes)))
        return size - log_file.stat().st_size


def clear_logs(log_dir: Path) -> tuple[int, int]:
    active = log_dir / 'mihomo.log'
    with _lock(active):
        previous_size = active.stat().st_size if active.exists() else 0
        fd = os.open(active, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        os.fchmod(fd, 0o600)
        os.close(fd)
        removed = 0
        for backup in log_dir.glob('mihomo.log.*'):
            if backup.is_file() and backup.name.rsplit('.', 1)[-1].isdigit():
                backup.unlink()
                removed += 1
        return previous_size, removed
