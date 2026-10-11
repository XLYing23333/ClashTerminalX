import io
import signal
from types import SimpleNamespace

import pytest

from clashtx.system import runner
from clashtx.system.service import ServiceManager
from test_security import identity, mock_processes


def test_runner_collects_output_without_any_ui_and_removes_record(store, monkeypatch):
    chunks = iter([b'failed node\n' * 1000, b'long line' * 1000, b''])
    exited = False
    class Child:
        pid = 301
        returncode = 0
        stdout = io.BytesIO()
        def poll(self): return 0 if exited else None
        def terminate(self): pass
        def kill(self): pass
        def wait(self, timeout=None): return 0
    child = Child()
    class Selector:
        active = True
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def register(self, *args): pass
        def unregister(self, *args): self.active = False
        def select(self, timeout): return [(SimpleNamespace(fd=9, fileobj=child.stdout), 1)] if self.active else []
        def get_map(self): return {9: True} if self.active else {}
    def read(fd, amount):
        nonlocal exited
        block = next(chunks)
        if not block: exited = True
        return block
    handlers = {}
    monkeypatch.setattr(runner.signal, 'signal', lambda sig, function: handlers.update({sig: function}))
    monkeypatch.setattr(runner.subprocess, 'Popen', lambda *args, **kwargs: child)
    monkeypatch.setattr(runner.selectors, 'DefaultSelector', Selector)
    monkeypatch.setattr(runner.os, 'read', read)
    monkeypatch.setattr(runner, 'process_identity', lambda pid: {'pid': pid})
    core = SimpleNamespace(build_command=lambda: ['mock-core'])
    assert runner.run(store, core) == 0
    assert not store.paths.pid_file.exists()
    assert b'failed node' in (store.paths.logs_dir / 'mihomo.log').read_bytes()


def test_start_failure_reclaims_only_the_created_runner(store, monkeypatch):
    service = ServiceManager(store)
    table = {401: {'pid': 401, 'start_time': '1', 'uid': 1, 'exe': 'mock-runner', 'args': []}}
    mock_processes(monkeypatch, table)
    monkeypatch.setattr(service.core, 'exists', lambda: True)
    monkeypatch.setattr(service, '_check_controller_free', lambda: None)
    monkeypatch.setattr(service, 'wait_until_ready', lambda timeout: False)
    child = SimpleNamespace(pid=401, wait=lambda timeout: 1)
    def launch(command, **kwargs):
        assert command[1:3] == ['-m', 'clashtx.system.runner']
        assert command[-2:] == ['--config-dir', str(store.paths.config_dir.resolve())]
        assert kwargs['env']['CLASHTX_CONFIG_DIR'] == str(store.paths.config_dir.resolve())
        return child
    monkeypatch.setattr('clashtx.system.service.subprocess.Popen', launch)
    killed = []
    monkeypatch.setattr(service, '_terminate_identity', lambda value: killed.append(value['pid']))
    with pytest.raises(RuntimeError, match='failed to become ready'):
        service.start()
    assert killed == [401]
    assert not store.paths.pid_file.exists()
    assert len(store.load_config().secret) >= 32


def test_occupied_controller_is_not_started_or_reconfigured(store, monkeypatch):
    service = ServiceManager(store)
    monkeypatch.setattr(service.core, 'exists', lambda: True)
    def occupied(): raise RuntimeError('controller address is occupied')
    monkeypatch.setattr(service, '_check_controller_free', occupied)
    with pytest.raises(RuntimeError, match='occupied'):
        service.start()
    assert not store.paths.app_config.exists()
    assert not store.paths.generated_config.exists()
