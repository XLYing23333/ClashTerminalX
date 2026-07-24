from __future__ import annotations

from pathlib import Path

DEFAULT_MAX_BYTES = 20 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 3
DEFAULT_KEEP_BYTES = 5 * 1024 * 1024


def rotate_log(
    log_file: Path,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> bool:
    """Rotate a stopped process log when it exceeds the configured limit."""
    try:
        if log_file.stat().st_size <= max_bytes:
            return False
    except FileNotFoundError:
        return False

    backup_count = max(1, backup_count)
    oldest = log_file.with_name(f"{log_file.name}.{backup_count}")
    oldest.unlink(missing_ok=True)
    for index in range(backup_count - 1, 0, -1):
        source = log_file.with_name(f"{log_file.name}.{index}")
        if source.exists():
            source.replace(log_file.with_name(f"{log_file.name}.{index + 1}"))
    log_file.replace(log_file.with_name(f"{log_file.name}.1"))
    return True


def trim_log(
    log_file: Path,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    keep_bytes: int = DEFAULT_KEEP_BYTES,
) -> int:
    """Keep only the tail of a live log file and return bytes removed."""
    try:
        size = log_file.stat().st_size
    except FileNotFoundError:
        return 0
    if size <= max_bytes:
        return 0

    keep_bytes = max(0, min(keep_bytes, max_bytes))
    with log_file.open("rb+") as handle:
        if keep_bytes:
            handle.seek(-keep_bytes, 2)
            tail = handle.read()
        else:
            tail = b""
        handle.seek(0)
        handle.write(tail)
        handle.truncate()
    return size - len(tail)


def clear_logs(log_dir: Path) -> tuple[int, int]:
    """Truncate the active log and delete rotated backups."""
    log_dir.mkdir(parents=True, exist_ok=True)
    active = log_dir / "mihomo.log"
    previous_size = active.stat().st_size if active.exists() else 0
    active.write_bytes(b"")

    removed_backups = 0
    for backup in log_dir.glob("mihomo.log.*"):
        if backup.is_file():
            backup.unlink()
            removed_backups += 1
    return previous_size, removed_backups
