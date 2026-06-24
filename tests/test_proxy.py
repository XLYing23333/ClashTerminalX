from clashtx.config import AppConfig, AppPaths, ConfigStore
from clashtx.system.proxy import ProxyManager


def test_proxy_manager_writes_env_file(tmp_path):
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
    store = ConfigStore(paths)
    store.save_config(
        AppConfig(
            mixed_port=7897,
            system_proxy_host="127.0.0.1",
            system_proxy_no_proxy="localhost,127.0.0.1",
        )
    )
    proxy = ProxyManager(store)

    env_path = proxy.enable()
    status = proxy.status()

    assert status.enabled is True
    assert env_path.exists()
    content = env_path.read_text(encoding="utf-8")
    assert "http://127.0.0.1:7897" in content
    assert "NO_PROXY=localhost,127.0.0.1" in content

    proxy.disable()
    status = proxy.status()

    assert status.enabled is False
    assert not env_path.exists()
