import pytest

from clashtx.config import AppConfig, AppPaths, ConfigStore
from clashtx.system.network import NetworkManager, NetworkModeError
from clashtx.system.proxy import ProxyManager
from clashtx.system.tun import TunManager


def _store(tmp_path):
    paths = AppPaths(
        config_dir=tmp_path / "config",
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        subscriptions_dir=tmp_path / "config" / "subscriptions",
        generated_config=tmp_path / "config" / "mihomo.yaml",
        app_config=tmp_path / "config" / "config.json",
        runtime_state=tmp_path / "config" / "state.json",
        core_dir=tmp_path / "data" / "core",
        logs_dir=tmp_path / "cache" / "logs",
        pid_file=tmp_path / "cache" / "mihomo.pid",
    )
    return ConfigStore(paths)


def test_tun_mode_disables_system_proxy(tmp_path, monkeypatch):
    store = _store(tmp_path)
    store.save_config(AppConfig(system_proxy_enabled=True))
    proxy = ProxyManager(store)
    proxy.enable()
    network = NetworkManager(store, proxy, TunManager(store))

    monkeypatch.setattr(TunManager, "ensure_environment", lambda self: None)
    monkeypatch.setattr(TunManager, "device_available", lambda self: True)

    message = network.set_mode("tun")

    config = store.load_config()
    assert config.network_mode == "tun"
    assert config.tun_enabled is True
    assert config.system_proxy_enabled is False
    assert not proxy.env_file.exists()
    assert "System proxy disabled" in message


def test_system_mode_enables_system_proxy(tmp_path):
    store = _store(tmp_path)
    store.save_config(AppConfig(network_mode="tun", tun_enabled=True))
    proxy = ProxyManager(store)
    network = NetworkManager(store, proxy, TunManager(store))

    message = network.set_mode("system")

    config = store.load_config()
    assert config.network_mode == "system"
    assert config.tun_enabled is False
    assert config.system_proxy_enabled is True
    assert proxy.env_file.exists()
    assert "System proxy enabled" in message


def test_proxy_enable_blocked_in_tun_mode(tmp_path):
    store = _store(tmp_path)
    store.save_config(AppConfig(network_mode="tun", tun_enabled=True))
    proxy = ProxyManager(store)
    network = NetworkManager(store, proxy, TunManager(store))

    with pytest.raises(NetworkModeError):
        network.ensure_proxy_allowed()

    with pytest.raises(RuntimeError):
        proxy.enable()
