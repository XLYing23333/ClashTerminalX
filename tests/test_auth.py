import json
import stat

import pytest
from fastapi.testclient import TestClient

from clashtx.controller import ClashTXController
from clashtx.web.app import create_app


def client_for(store, password=None, base_url='http://127.0.0.1'):
    return TestClient(create_app(ClashTXController(store), password=password), base_url=base_url)


def login(client, password='7897'):
    response = client.post('/api/auth/login', json={'password': password})
    assert response.status_code == 200
    client.headers['X-CSRF-Token'] = response.json()['csrf_token']
    return response


def test_unauthenticated_interfaces_are_protected(store):
    client = client_for(store)
    assert client.get('/').status_code == 200
    assert client.get('/static/app.js').status_code == 200
    for path in ['/api/dashboard', '/api/subscriptions', '/api/nodes', '/api/docs', '/openapi.json', '/api/auth/session']:
        assert client.get(path).status_code == 401
    assert client.post('/api/service/stop').status_code == 401


def test_password_persistence_hash_and_private_permissions(store):
    client = client_for(store, 'new-password')
    assert client.post('/api/auth/login', json={'password': '7897'}).status_code == 401
    login(client, 'new-password')
    restarted = client_for(store)
    assert restarted.post('/api/auth/login', json={'password': 'new-password'}).status_code == 200
    path = store.paths.config_dir / 'web-auth.json'
    raw = path.read_text()
    assert 'new-password' not in raw
    assert json.loads(raw)['iterations'] == 600_000
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert not store.load_config().secret  # Web password is not a Mihomo credential.


def test_empty_password_rejected(store):
    with pytest.raises(ValueError):
        create_app(ClashTXController(store), password='')


def test_csrf_logout_cookie_and_expiry(store):
    app = create_app(ClashTXController(store))
    client = TestClient(app, base_url="http://127.0.0.1")
    response = login(client)
    assert 'HttpOnly' in response.headers['set-cookie']
    assert 'SameSite=strict' in response.headers['set-cookie']
    assert client.get('/api/dashboard').status_code == 200
    csrf = client.headers.pop('X-CSRF-Token')
    assert client.post('/api/sort', json={'sort_mode': 'a-z'}).status_code == 403
    client.headers['X-CSRF-Token'] = csrf
    assert client.post('/api/sort', json={'sort_mode': 'a-z'}).status_code == 200
    assert client.post('/api/auth/logout').status_code == 200
    assert client.get('/api/dashboard').status_code == 401
    login(client)
    app.state.auth.sessions = {key: (0, value[1]) for key, value in app.state.auth.sessions.items()}
    assert client.get('/api/dashboard').status_code == 401


def test_password_change_and_restart_invalidate_sessions(store):
    app = create_app(ClashTXController(store))
    client = TestClient(app, base_url="http://127.0.0.1")
    login(client)
    app.state.auth.set_password('changed')
    assert client.get('/api/dashboard').status_code == 401
    login(client, 'changed')
    restarted = client_for(store)
    restarted.cookies.update(client.cookies)
    assert restarted.get('/api/dashboard').status_code == 401


def test_failed_login_rate_limit_and_https_cookie(store):
    client = client_for(store, base_url='https://127.0.0.1')
    for _ in range(5):
        assert client.post('/api/auth/login', json={'password': 'wrong'}).status_code == 401
    assert client.post('/api/auth/login', json={'password': '7897'}).status_code == 429
    client = TestClient(create_app(ClashTXController(store)), base_url='https://127.0.0.1')
    assert 'Secure' in login(client).headers['set-cookie']


def test_loopback_host_rejects_dns_rebinding(store):
    client = client_for(store, base_url='http://attacker.example')
    assert client.post('/api/auth/login', json={'password': '7897'}).status_code == 400


def test_ipv6_loopback_host_is_supported(store):
    client = TestClient(create_app(ClashTXController(store), host='::1'), base_url='http://127.0.0.1', headers={'Host': '[::1]'})
    assert client.get('/').status_code == 200
    login(client)
    assert client.get('/api/dashboard').status_code == 200


def test_invalid_password_is_not_echoed_in_validation_response(store):
    client = client_for(store)
    password = 'private-invalid-input' * 20
    response = client.post('/api/auth/login', json={'password': password})
    assert response.status_code == 422
    assert password not in response.text
    response = client.post('/api/auth/login', json={'password': 123456789})
    assert response.status_code == 422
    assert '123456789' not in response.text
