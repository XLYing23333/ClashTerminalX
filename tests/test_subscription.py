import pytest

from clashtx.config import AppConfig, AppPaths, ConfigStore, Subscription
from clashtx.subscription import SubscriptionManager, parse_subscription_yaml, sort_nodes


def test_sort_nodes_by_latency_then_name():
    nodes = ["Hong Kong", "Japan", "Auto"]
    latency = {"Japan": 60, "Hong Kong": 20}

    assert sort_nodes(nodes, "latency", latency) == ["Hong Kong", "Japan", "Auto"]


def test_sort_nodes_alphabetically():
    nodes = ["beta", "Alpha", "gamma"]

    assert sort_nodes(nodes, "a-z") == ["Alpha", "beta", "gamma"]
    assert sort_nodes(nodes, "z-a") == ["gamma", "beta", "Alpha"]


def test_parse_subscription_yaml_rejects_html():
    with pytest.raises(ValueError, match="not valid YAML|not a YAML mapping|does not look like"):
        parse_subscription_yaml("<html><body>403</body></html>")


def test_delete_subscription_updates_active(tmp_path):
    store = ConfigStore(
        AppPaths(
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
    )
    sub_file = store.paths.subscriptions_dir / "demo.yaml"
    sub_file.write_text("proxies: []\nproxy-groups: []\n", encoding="utf-8")
    store.save_config(
        AppConfig(
            subscriptions=[Subscription("demo", "https://example.test", "demo.yaml")],
            active_subscription="demo",
        )
    )

    SubscriptionManager(store).delete("demo")

    assert store.load_config().subscriptions == []
    assert store.load_config().active_subscription is None
    assert not sub_file.exists()


def test_update_subscription_does_not_change_active(tmp_path, monkeypatch):
    store = ConfigStore(
        AppPaths(
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
    )
    active_file = store.paths.subscriptions_dir / "active.yaml"
    inactive_file = store.paths.subscriptions_dir / "inactive.yaml"
    active_file.write_text("proxies: []\nproxy-groups: []\n", encoding="utf-8")
    inactive_file.write_text("proxies: []\nproxy-groups: []\n", encoding="utf-8")
    store.save_config(
        AppConfig(
            subscriptions=[
                Subscription("active", "https://example.test/active", "active.yaml"),
                Subscription("inactive", "https://example.test/inactive", "inactive.yaml"),
            ],
            active_subscription="active",
        )
    )
    manager = SubscriptionManager(store)
    monkeypatch.setattr(
        manager,
        "download",
        lambda _url: "proxies:\n- name: new\n  type: direct\nproxy-groups: []\n",
    )

    updated = manager.update("inactive")

    config = store.load_config()
    assert updated.name == "inactive"
    assert config.active_subscription == "active"
    assert "name: new" in inactive_file.read_text(encoding="utf-8")


def test_add_or_update_subscription_does_not_change_active(tmp_path, monkeypatch):
    store = ConfigStore(
        AppPaths(
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
    )
    active_file = store.paths.subscriptions_dir / "active.yaml"
    active_file.write_text("proxies: []\nproxy-groups: []\n", encoding="utf-8")
    store.save_config(
        AppConfig(
            subscriptions=[Subscription("active", "https://example.test/active", "active.yaml")],
            active_subscription="active",
        )
    )
    manager = SubscriptionManager(store)
    monkeypatch.setattr(
        manager,
        "download",
        lambda _url: "proxies:\n- name: new\n  type: direct\nproxy-groups: []\n",
    )

    created = manager.add_or_update("inactive", "https://example.test/inactive")

    config = store.load_config()
    assert created.name == "inactive"
    assert config.active_subscription == "active"
