import httpx

from clashtx.config import AppConfig, AppPaths, ConfigStore
from clashtx.mihomo import MihomoAPI


def test_select_node_saves_choice(monkeypatch, tmp_path):
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
    store.save_config(AppConfig(external_controller="127.0.0.1:9090"))
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    transport = httpx.MockTransport(handler)
    original_client = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)

    MihomoAPI(store).select_node("良心云", "日本 节点")

    assert requests[0].method == "PUT"
    assert requests[0].url.path.endswith("良心云") or requests[0].url.path.endswith(
        "%E8%89%AF%E5%BF%83%E4%BA%91"
    )
    assert store.load_config().selected_nodes["良心云"] == "日本 节点"


def test_reload_config_calls_configs_endpoint(monkeypatch, tmp_path):
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
    store.save_config(AppConfig(external_controller="127.0.0.1:9090"))
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    transport = httpx.MockTransport(handler)
    original_client = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)

    MihomoAPI(store).reload_config()

    assert requests[0].method == "PUT"
    assert requests[0].url.path == "/configs"
    assert requests[0].url.params["force"] == "true"
