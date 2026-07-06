from fastapi.testclient import TestClient

from clashtx.config import AppConfig, AppPaths, ConfigStore
from clashtx.controller import ClashTXController
from clashtx.web.app import create_app


def test_web_dashboard_endpoint(tmp_path):
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
    store.save_config(AppConfig(mixed_port=7897, proxy_mode="rule"))
    client = TestClient(create_app(ClashTXController(store)))

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["active"] is False
    assert payload["proxy_port"] == 7897
    assert payload["mode"] == "rule"


def test_web_network_mode_endpoint(tmp_path, monkeypatch):
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
    store.save_config(AppConfig(network_mode="system"))
    ctl = ClashTXController(store)
    monkeypatch.setattr(
        ClashTXController,
        "set_network_mode",
        lambda self, mode: f"Switched to {mode}",
    )
    client = TestClient(create_app(ctl))

    response = client.post("/api/network/mode", json={"mode": "tun"})

    assert response.status_code == 200
    assert "tun" in response.json()["message"]


def test_web_proxy_mode_rejects_network_mode_values(tmp_path, monkeypatch):
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
    client = TestClient(create_app(ClashTXController(ConfigStore(paths))))

    response = client.post("/api/mode", json={"mode": "system"})

    assert response.status_code == 400
    assert "/api/network/mode" in response.json()["detail"]


def test_web_refresh_all_subscriptions_endpoint(tmp_path, monkeypatch):
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
    ctl = ClashTXController(ConfigStore(paths))
    monkeypatch.setattr(
        ClashTXController,
        "refresh_all_subscriptions",
        lambda self: {
            "successful": ["ok"],
            "failed": [{"name": "bad", "error": "boom"}],
            "success_count": 1,
            "failure_count": 1,
            "message": "done",
        },
    )
    client = TestClient(create_app(ctl))

    response = client.post("/api/subscriptions/refresh-all")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success_count"] == 1
    assert payload["failure_count"] == 1


def test_web_index_page(tmp_path):
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
    client = TestClient(create_app(ClashTXController(ConfigStore(paths))))

    response = client.get("/")

    assert response.status_code == 200
    assert "ClashTX" in response.text
    assert "/static/logo.png" in response.text


def test_web_logo_assets(tmp_path):
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
    client = TestClient(create_app(ClashTXController(ConfigStore(paths))))

    logo = client.get("/static/logo.png")
    favicon = client.get("/static/favicon.png")

    assert logo.status_code == 200
    assert favicon.status_code == 200
    assert logo.headers["content-type"].startswith("image/")
