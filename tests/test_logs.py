import os
import threading
from pathlib import Path

from clashtx.system.logs import BoundedLog, clear_logs


def test_default_log_limit_under_more_than_80_mib_of_output(tmp_path):
    path = tmp_path / 'mihomo.log'
    writer = BoundedLog(path)
    block = b'failed-node\n' * 5000
    for _ in range(1800):
        writer.write(block)
    files = list(tmp_path.glob('mihomo.log*'))
    assert len(files) == 4
    assert all(file.stat().st_size <= 20 * 1024 * 1024 for file in files)
    assert sum(file.stat().st_size for file in files) <= 80 * 1024 * 1024
    assert writer.dropped_bytes == 0


def test_oversized_history_and_long_line_have_bounded_total(tmp_path):
    path = tmp_path / 'mihomo.log'
    for suffix in ['', '.1', '.2', '.3', '.4']:
        (tmp_path / ('mihomo.log' + suffix)).write_bytes(b'a' * 10000)
    writer = BoundedLog(path, max_bytes=512)
    assert not path.with_name('mihomo.log.4').exists()
    writer.write(b'long-line-without-newlines' * 2000)
    files = list(tmp_path.glob('mihomo.log*'))
    assert len(files) == 4
    assert sum(file.stat().st_size for file in files) <= 2048


def test_concurrent_clean_and_writer_keep_limits(tmp_path):
    path = tmp_path / 'mihomo.log'
    writer = BoundedLog(path, max_bytes=512)
    threads = [threading.Thread(target=lambda: [writer.write(b'x' * 200) for _ in range(60)]),
               threading.Thread(target=lambda: [clear_logs(tmp_path) for _ in range(20)])]
    for thread in threads: thread.start()
    for thread in threads: thread.join(timeout=5)
    assert all(not thread.is_alive() for thread in threads)
    assert all(file.stat().st_size <= 512 for file in tmp_path.glob('mihomo.log*'))


def test_disk_error_drops_data_then_recovers(tmp_path, monkeypatch):
    path = tmp_path / 'mihomo.log'
    writer = BoundedLog(path, max_bytes=512)
    real_open = os.open
    def failing_open(file, *args, **kwargs):
        if Path(file) == path:
            raise OSError('disk full')
        return real_open(file, *args, **kwargs)
    monkeypatch.setattr(os, 'open', failing_open)
    writer.write(b'cannot persist')
    assert writer.dropped_bytes == len(b'cannot persist')
    monkeypatch.setattr(os, 'open', real_open)
    writer.write(b'recovered')
    assert path.read_bytes() == b'recovered'
