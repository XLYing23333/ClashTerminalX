"""All tests use isolated paths; real system/desktop/core operations are forbidden."""
import subprocess

import httpx
import pytest

from clashtx.config import AppPaths, ConfigStore
from clashtx.core import CoreManager
from clashtx.system.service import ServiceManager


@pytest.fixture(autouse=True)
def isolated_system(tmp_path, monkeypatch):
    for key, directory in [('CLASHTX_CONFIG_DIR', 'config'), ('CLASHTX_DATA_DIR', 'data'), ('CLASHTX_CACHE_DIR', 'cache')]:
        monkeypatch.setenv(key, str(tmp_path / directory))
    def forbidden(*args, **kwargs):
        raise AssertionError('Real core/process/network operation forbidden in isolated tests')
    def system_run(args, **kwargs):
        if args[0] in {'gsettings', 'getcap', 'setcap', 'modprobe', 'systemctl'}:
            return subprocess.CompletedProcess(args, 0, "'none'\n" if args[0] == 'gsettings' else '', '')
        return forbidden(args, **kwargs)
    monkeypatch.setattr(subprocess, 'run', system_run)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(CoreManager, 'version', lambda self: 'mock-core')
    monkeypatch.setattr('clashtx.system.proxy.ProxyManager.port_open', lambda self, port=None: False)
    # Safety barrier even if a process-management test forgets to mock its signal path.
    monkeypatch.setattr('os.kill', forbidden)
    if hasattr(__import__('signal'), 'pidfd_send_signal'):
        monkeypatch.setattr('signal.pidfd_send_signal', forbidden)
    monkeypatch.setattr('socket.socket.connect', forbidden)
    monkeypatch.setattr('socket.socket.bind', forbidden)
    monkeypatch.setattr('httpx.HTTPTransport.handle_request', forbidden)


@pytest.fixture
def store():
    return ConfigStore()


@pytest.fixture
def own_api(monkeypatch):
    monkeypatch.setattr(ServiceManager, 'assert_api_owner', lambda self: None)


@pytest.fixture
def logged_client():
    from fastapi.testclient import TestClient
    def make(app):
        client = TestClient(app, base_url="http://127.0.0.1")
        response = client.post('/api/auth/login', json={'password': '7897'})
        assert response.status_code == 200
        client.headers['X-CSRF-Token'] = response.json()['csrf_token']
        return client
    return make
