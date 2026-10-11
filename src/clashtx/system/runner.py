"""Detached output collector. No UI or desktop proxy operations are performed here."""
from __future__ import annotations

import argparse
import json
import os
import selectors
import signal
import subprocess
import time

from clashtx.config import ConfigStore
from clashtx.config.store import _write_json
from clashtx.core import CoreManager
from clashtx.system.logs import BoundedLog, CHUNK_BYTES
from clashtx.system.process import process_identity


def run(store: ConfigStore, core: CoreManager) -> int:
    stop_requested = False
    def stop(signum, frame):
        nonlocal stop_requested
        stop_requested = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    writer = BoundedLog(store.paths.logs_dir / 'mihomo.log')
    process = None
    runner = process_identity(os.getpid())
    try:
        process = subprocess.Popen(core.build_command(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        identity = process_identity(process.pid)
        if identity is None:
            raise RuntimeError('Mihomo exited before its process identity could be recorded.')
        _write_json(store.paths.pid_file, {'version': 1, 'core': identity, 'runner': runner,
                                         'controller': store.load_config().external_controller})
        deadline = None
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                if stop_requested and deadline is None:
                    process.terminate()  # Popen owns this child; no PID-file lookup.
                    deadline = time.monotonic() + 5
                if deadline is not None and time.monotonic() >= deadline and process.poll() is None:
                    process.kill()
                for key, events in selector.select(timeout=0.1):
                    block = os.read(key.fd, CHUNK_BYTES)
                    if block:
                        writer.write(block)
                    else:
                        selector.unregister(key.fileobj)
                if process.poll() is not None and not selector.get_map():
                    return process.returncode
    except Exception:
        # Do not put command arguments, passwords or subscription contents into errors.
        writer.write(b'ClashTX runner failed to start or collect core output.\n')
        return 1
    finally:
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            if process.stdout is not None:
                process.stdout.close()
        try:
            record = json.loads(store.paths.pid_file.read_text())
            if record.get('runner') == runner:
                store.paths.pid_file.unlink(missing_ok=True)
        except (OSError, ValueError, AttributeError):
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config-dir', required=True)
    options = parser.parse_args()
    os.environ['CLASHTX_CONFIG_DIR'] = options.config_dir
    store = ConfigStore()
    raise SystemExit(run(store, CoreManager(store)))
