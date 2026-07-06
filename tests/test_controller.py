from clashtx.controller import (
    build_group_nodes,
    collect_testable_nodes,
    groups_to_sync,
    is_proxy_node,
    is_selectable_group,
    pick_active_node_group,
    pick_primary_node,
    ClashTXController,
)
from clashtx.config import AppConfig, AppPaths, ConfigStore
from clashtx.mihomo.api import ProxyGroup


def test_groups_to_sync_includes_global_for_leaf_node():
    groups = {
        "GLOBAL": ProxyGroup("GLOBAL", "Selector", "old", ["node-a", "良心云"]),
        "良心云": ProxyGroup("良心云", "Selector", "old", ["node-a", "node-b"]),
        "自动选择": ProxyGroup("自动选择", "URLTest", "node-a", ["node-a"]),
    }

    synced = groups_to_sync(groups, "良心云", "node-a")

    assert synced == ["良心云", "GLOBAL"]


def test_is_proxy_node_rejects_auto_group_names():
    assert is_proxy_node("日本 01 | 专线") is True
    assert is_proxy_node("自动选择") is False
    assert is_proxy_node("DIRECT") is False


def test_pick_active_node_group_prefers_saved_group():
    groups = [
        {"name": "GLOBAL", "selectable": True, "nodes": [{"node": "a"}]},
        {"name": "良心云", "selectable": True, "nodes": [{"node": "b"}]},
    ]

    assert pick_active_node_group(groups, "良心云") == "良心云"
    assert pick_active_node_group(groups, None) == "GLOBAL"


def test_pick_primary_node_prefers_active_group_over_global():
    groups = [
        ProxyGroup("GLOBAL", "Selector", "global-node", ["global-node"]),
        ProxyGroup("良心云", "Selector", "selected-node", ["selected-node"]),
    ]

    assert (
        pick_primary_node(groups, preferred_group="良心云")
        == "良心云 -> selected-node"
    )


def test_pick_primary_node_prefers_saved_active_group_when_api_unavailable():
    assert (
        pick_primary_node(
            [],
            from_config={"GLOBAL": "global-node", "良心云": "selected-node"},
            preferred_group="良心云",
        )
        == "良心云 -> selected-node"
    )


def test_build_group_nodes_filters_pseudo_entries():
    group = ProxyGroup(
        "良心云",
        "Selector",
        "🇯🇵日本高速01|CTCU|0.5x",
        ["自动选择", "剩余流量：1 GB", "🇯🇵日本高速01|CTCU|0.5x"],
    )

    nodes = build_group_nodes(group, sort_mode="a-z", latency_ms={})

    assert [item["node"] for item in nodes] == ["🇯🇵日本高速01|CTCU|0.5x"]


def test_collect_testable_nodes_deduplicates():
    groups = [
        ProxyGroup("GLOBAL", "Selector", None, ["node-a", "node-b"]),
        ProxyGroup("良心云", "Selector", None, ["node-a", "node-c"]),
    ]

    assert collect_testable_nodes(groups) == ["node-a", "node-b", "node-c"]


def test_test_all_nodes_does_not_select_fastest_or_change_sort(tmp_path, monkeypatch):
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
    store.save_config(AppConfig(sort_mode="a-z"))
    controller = ClashTXController(store)
    monkeypatch.setattr(
        controller.api,
        "groups",
        lambda: [ProxyGroup("GLOBAL", "Selector", "node-a", ["node-a", "node-b"])],
    )
    monkeypatch.setattr(
        controller.api,
        "delay",
        lambda node, timeout_ms=3000, persist=False: 10 if node == "node-b" else 20,
    )
    monkeypatch.setattr(
        controller,
        "select_node",
        lambda group, node: (_ for _ in ()).throw(AssertionError("should not select")),
    )

    result = controller.test_all_nodes(max_workers=1)

    assert result["fastest"] == "node-b"
    assert store.load_config().sort_mode == "a-z"


def test_is_selectable_group_only_allows_selector():
    assert is_selectable_group(ProxyGroup("良心云", "Selector", None, [])) is True
    assert is_selectable_group(ProxyGroup("自动选择", "URLTest", None, [])) is False
