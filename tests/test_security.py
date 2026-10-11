import json
import os
import shlex
import stat
import threading
from pathlib import Path

import pytest

from clashtx.config import AppConfig, Subscription
from clashtx.config.store import _write_json
from clashtx.controller import ClashTXController
from clashtx.mihomo import MihomoAPI
from clashtx.subscription import SubscriptionManager
from clashtx.system.process import is_core
from clashtx.system.proxy import ProxyManager, validate_settings
from clashtx.system.service import ServiceManager


@pytest.mark.parametrize('host,port,no_proxy', [
    ('127.0.0.1; echo attack', 7897, 'localhost'),
    ('$(echo attack)', 7897, 'localhost'),
    ('http://example.com', 7897, 'localhost'),
    ('localhost', 0, ''), ('localhost', 65536, ''),
    ('localhost', 7897, 'localhost\ncommand'),
])
def test_reject_unsafe_proxy_settings_before_write(store, host, port, no_proxy):
    with pytest.raises(ValueError):
        ProxyManager(store).apply_settings(host, port, no_proxy)
    assert not store.paths.app_config.exists()


def test_shell_values_are_literal_and_private(store):
    payload = "localhost; $(echo unsafe) 'quoted'"
    store.save_config(AppConfig(system_proxy_no_proxy=payload))
    path = ProxyManager(store).enable()
    lines = path.read_text().splitlines()
    for line in lines:
        words = shlex.split(line)
        assert len(words) == 2 and words[0] == 'export'
        if words[1].startswith(('no_proxy=', 'NO_PROXY=')):
            assert words[1].split('=', 1)[1] == payload
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert validate_settings('::1', 7897, '')[0] == '::1'


def test_chinese_subscriptions_cannot_overwrite_or_delete_each_other(store, monkeypatch):
    manager = SubscriptionManager(store)
    monkeypatch.setattr(manager, 'download', lambda url: f'proxies: []\nproxy-groups: []\nmarker: {url}\n')
    first = manager.add_or_update('机场甲', 'first')
    manager.activate(first.name)
    second = manager.add_or_update('机场乙', 'second')
    assert first.file != second.file
    assert store.read_generated_config()['marker'] == 'first'
    manager.delete(second.name)
    assert (store.paths.subscriptions_dir / first.file).exists()
    assert store.read_generated_config()['marker'] == 'first'
    assert manager.add_or_update(first.name, 'new').file == first.file


def test_shared_legacy_file_migrates_without_download_and_has_backup(store, monkeypatch):
    store.save_config(AppConfig(subscriptions=[Subscription('甲', 'url-a', 'subscription.yaml'),
                                               Subscription('乙', 'url-b', 'subscription.yaml')], active_subscription='甲'))
    (store.paths.subscriptions_dir / 'subscription.yaml').write_text('proxies: []\nproxy-groups: []\n')
    manager = SubscriptionManager(store)
    monkeypatch.setattr(manager, 'download', lambda url: pytest.fail('migration must not download'))
    with pytest.warns(UserWarning, match='shared file'):
        manager.activate('甲')
    config = store.load_config()
    assert len({item.file for item in config.subscriptions}) == 2
    assert len(config.migration_warnings) == 2
    backup, = store.paths.config_dir.glob('subscription-backup-*')
    assert (backup / 'subscription.yaml').exists()
    assert (backup / 'config.json').exists()
    manager.delete('乙')
    assert (store.paths.subscriptions_dir / config.subscriptions[0].file).exists()


def test_managed_settings_survive_subscription_and_script(store):
    store.save_config(AppConfig(secret='core-secret'))
    store.paths.global_script.write_text("def main(config):\n config.update({'secret':'wrong','external-controller':'0.0.0.0:9090','log-level':'debug'})\n return config\n")
    generated = SubscriptionManager(store).generate_runtime_config(source={'log-level': 'info'})
    assert generated['log-level'] == 'warning'
    assert generated['secret'] == 'core-secret'
    assert generated['external-controller'] == '127.0.0.1:19090'


def test_inactive_core_never_receives_mutating_requests(store, monkeypatch):
    controller = ClashTXController(store)
    monkeypatch.setattr(controller.api, 'reload_config', lambda: pytest.fail('must not call another core'))
    assert controller._reload_config_message().startswith('Config saved.')
    with pytest.raises(RuntimeError, match='No verified'):
        MihomoAPI(store).set_mode('direct')


def identity(service, pid=201):
    config = service.store.load_config()
    return {'pid': pid, 'uid': os.getuid(), 'start_time': '10', 'exe': str(service.core.binary_path.resolve()),
            'args': [str(service.core.binary_path), '-d', str(service.store.paths.config_dir),
                     '-f', str(service.store.paths.generated_config), '-ext-ctl', config.external_controller]}


def mock_processes(monkeypatch, table):
    reader = lambda pid: table.get(pid)
    monkeypatch.setattr('clashtx.system.process.process_identity', reader)
    monkeypatch.setattr('clashtx.system.service.process_identity', reader)
    monkeypatch.setattr('clashtx.system.service.process_exists', lambda pid: pid in table)


def test_editor_and_reused_pid_cannot_be_killed(store, monkeypatch):
    service = ServiceManager(store)
    editor = {'pid': 201, 'uid': os.getuid(), 'exe': '/usr/bin/vim', 'start_time': '11',
              'args': ['vim', str(store.paths.generated_config)]}
    mock_processes(monkeypatch, {201: editor})
    store.paths.pid_file.write_text('201')
    assert not is_core(editor, service.core.binary_path, store.paths.generated_config)
    assert service.status().active is False
    with pytest.raises(RuntimeError, match='unverified'):
        service.stop()
    record = identity(service)
    _write_json(store.paths.pid_file, {'version': 1, 'core': record, 'runner': None, 'controller': store.load_config().external_controller})
    with pytest.raises(RuntimeError, match='reused'):
        service.stop()


def test_legacy_core_requires_exact_identity_and_listener(store, monkeypatch):
    service = ServiceManager(store)
    record = identity(service)
    mock_processes(monkeypatch, {201: record})
    store.paths.pid_file.write_text('201')
    assert service.status().active
    assert 'Legacy core' in service.status().text
    monkeypatch.setattr('clashtx.system.service.owns_listener', lambda *args: False)
    with pytest.raises(RuntimeError, match='listener'):
        service.assert_api_owner()
    monkeypatch.setattr('clashtx.system.service.owns_listener', lambda *args: True)
    service.assert_api_owner()


def test_config_transactions_do_not_lose_concurrent_updates(store):
    def update(name):
        with store.transaction():
            config = store.load_config()
            config.selected_nodes[name] = name
            store.save_config(config)
    threads = [threading.Thread(target=update, args=(str(index),)) for index in range(12)]
    for thread in threads: thread.start()
    for thread in threads: thread.join(timeout=5)
    assert len(store.load_config().selected_nodes) == 12


def test_reading_status_does_not_trim_or_write_logs(store):
    log = store.paths.logs_dir / 'mihomo.log'
    log.write_bytes(b'x' * 100)
    ServiceManager(store).status()
    assert log.read_bytes() == b'x' * 100


def test_subscription_file_traversal_is_rejected(store):
    manager = SubscriptionManager(store)
    with pytest.raises(ValueError, match='path'):
        manager._path('../outside.yaml')


def test_config_and_yaml_are_private(store):
    store.save_config(AppConfig(secret='private'))
    SubscriptionManager(store).generate_runtime_config()
    for file in [store.paths.app_config, store.paths.generated_config]:
        assert stat.S_IMODE(file.stat().st_mode) == 0o600


def test_install_entrypoint_template_matches():
    root = Path(__file__).resolve().parents[1]
    assert (root / 'clashtx.sh').read_bytes() == (root / 'scripts/clashtx-entry.sh').read_bytes()


def test_unreadable_process_identity_is_not_treated_as_a_dead_core(store, monkeypatch):
    service = ServiceManager(store)
    record = identity(service)
    _write_json(store.paths.pid_file, {'version': 1, 'core': record, 'runner': None, 'controller': store.load_config().external_controller})
    monkeypatch.setattr('clashtx.system.service.process_identity', lambda pid: None)
    monkeypatch.setattr('clashtx.system.service.process_exists', lambda pid: True)
    with pytest.raises(RuntimeError, match='cannot be read'):
        service.stop()
    assert store.paths.pid_file.exists()


def test_legacy_default_controller_can_be_identified_after_upgrade(store, monkeypatch):
    service = ServiceManager(store)
    record = identity(service)
    record['args'][-1] = '127.0.0.1:9090'
    mock_processes(monkeypatch, {201: record})
    store.paths.pid_file.write_text('201')
    assert service.status().active
    assert service._record()['controller'] == '127.0.0.1:9090'
    # Do not send API requests using the new default address to another process.
    with pytest.raises(RuntimeError, match='No verified'):
        service.assert_api_owner()


@pytest.mark.parametrize('record', [True, 0, {'version':1, 'core':{'pid':'201'}}, {'version':1, 'core':{}}])
def test_malformed_identity_fails_closed(store, record):
    store.paths.pid_file.write_text(json.dumps(record))
    with pytest.raises(RuntimeError, match='Invalid'):
        ServiceManager(store).stop()
