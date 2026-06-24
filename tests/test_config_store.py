from clashtx.config import AppConfig, AppPaths, ConfigStore, Subscription


def test_config_store_round_trip(tmp_path):
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
    config = AppConfig(
        subscriptions=[Subscription("demo", "https://example.test/sub", "demo.yaml")],
        active_subscription="demo",
        proxy_mode="global",
        tun_enabled=True,
    )

    store.save_config(config)
    loaded = store.load_config()

    assert loaded.active_subscription == "demo"
    assert loaded.proxy_mode == "global"
    assert loaded.tun_enabled is True
    assert loaded.subscriptions[0].name == "demo"


def test_config_store_recovers_trailing_json_garbage(tmp_path):
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
    paths.app_config.write_text('{"active_subscription": "demo"}\\n}\\n', encoding="utf-8")

    loaded = store.load_config()

    assert loaded.active_subscription == "demo"
    assert paths.app_config.read_text(encoding="utf-8").strip() == '{\n  "active_subscription": "demo"\n}'
