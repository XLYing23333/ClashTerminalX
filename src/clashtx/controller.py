from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from typing import Any

from clashtx.config import ConfigStore
from clashtx.core import CoreManager
from clashtx.mihomo import MihomoAPI
from clashtx.mihomo.api import ProxyGroup
from clashtx.subscription import SubscriptionManager, sort_nodes
from clashtx.system import ServiceManager
from clashtx.system.network import NetworkManager, NetworkModeError
from clashtx.system.proxy import ProxyManager
from clashtx.system.capabilities import core_has_tun_capabilities, grant_caps_command
from clashtx.system.tun import TunManager

NON_PROXY_NODES = {"DIRECT", "REJECT"}
NON_PROXY_PREFIXES = (
    "剩余流量",
    "距离下次",
    "套餐到期",
    "请立即",
    "更新于",
    "邀请",
)
AUTO_GROUPS = {"自动选择", "故障转移"}
PRIMARY_GROUPS = ("GLOBAL", "良心云")
SELECTABLE_GROUP_TYPES = {"Selector"}
ProgressCallback = Callable[[int, int, str | None], None]
DEFAULT_TEST_ALL_WORKERS = 12


@dataclass(slots=True)
class TestAllProgress:
    running: bool = False
    done: int = 0
    total: int = 0
    current: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


def is_proxy_node(node: str) -> bool:
    return (
        node not in NON_PROXY_NODES
        and node not in AUTO_GROUPS
        and not node.startswith(NON_PROXY_PREFIXES)
    )


def is_selectable_group(group: ProxyGroup) -> bool:
    return group.name not in AUTO_GROUPS and group.type in SELECTABLE_GROUP_TYPES


def groups_to_sync(groups: dict[str, ProxyGroup], primary_group: str, node: str) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        if name in seen:
            return
        group = groups.get(name)
        if group is None or not is_selectable_group(group):
            return
        if node not in group.all:
            return
        seen.add(name)
        ordered.append(name)

    add(primary_group)
    if primary_group != "GLOBAL":
        add("GLOBAL")
    for name in sorted(groups):
        add(name)
    return ordered


def sort_proxy_groups(groups: list[ProxyGroup]) -> list[ProxyGroup]:
    priority = {name: index for index, name in enumerate(PRIMARY_GROUPS)}

    def sort_key(group: ProxyGroup) -> tuple[int, str]:
        if group.name in priority:
            return (0, str(priority[group.name]))
        if is_selectable_group(group):
            return (1, group.name.casefold())
        return (2, group.name.casefold())

    return sorted(groups, key=sort_key)


def build_group_nodes(
    group: ProxyGroup,
    *,
    sort_mode: str,
    latency_ms: dict[str, int],
) -> list[dict[str, Any]]:
    nodes = sort_nodes(group.all, sort_mode, latency_ms)
    entries: list[dict[str, Any]] = []
    for node in nodes:
        if not is_proxy_node(node):
            continue
        delay = latency_ms.get(node)
        entries.append(
            {
                "node": node,
                "delay": delay,
                "selected": group.now == node,
                "selectable": is_selectable_group(group),
            }
        )
    return entries


def pick_active_node_group(
    groups: list[dict[str, Any]], preferred: str | None = None
) -> str | None:
    names = [group["name"] for group in groups if group["nodes"]]
    if preferred and preferred in names:
        return preferred
    for name in PRIMARY_GROUPS:
        if name in names:
            return name
    for group in groups:
        if group["selectable"] and group["nodes"]:
            return group["name"]
    return names[0] if names else None


def format_test_all_message(result: dict[str, Any], *, phase: str = "done") -> str:
    if phase == "start":
        total = result.get("total", 0)
        return f"Starting concurrent latency test for {total} nodes..."
    if phase == "running":
        done = result.get("done", 0)
        total = result.get("total", 0)
        current = result.get("current") or "..."
        return f"Testing nodes {done}/{total} — {current}"
    tested = result.get("tested", 0)
    total = result.get("total", 0)
    failed = result.get("failed", 0)
    fastest = result.get("fastest") or "none"
    fastest_delay = result.get("fastest_delay")
    delay_text = f" ({fastest_delay} ms)" if fastest_delay is not None else ""
    return (
        f"Latency test complete: {tested}/{total} succeeded, {failed} failed. "
        f"Fastest: {fastest}{delay_text}"
    )


def collect_testable_nodes(groups: list[ProxyGroup]) -> list[str]:
    seen: set[str] = set()
    nodes: list[str] = []
    for group in groups:
        for node in group.all:
            if node in seen or not is_proxy_node(node):
                continue
            seen.add(node)
            nodes.append(node)
    return nodes


def pick_primary_node(
    groups: list[ProxyGroup],
    *,
    from_config: dict[str, str] | None = None,
    preferred_group: str | None = None,
) -> str:
    if preferred_group:
        for group in groups:
            if group.name == preferred_group and group.now:
                return f"{group.name} -> {group.now}"
        if from_config and preferred_group in from_config:
            return f"{preferred_group} -> {from_config[preferred_group]}"
    if groups:
        for preferred in PRIMARY_GROUPS:
            for group in groups:
                if group.name == preferred and group.now:
                    return f"{group.name} -> {group.now}"
        for group in groups:
            if (
                group.type == "Selector"
                and group.now
                and group.name not in AUTO_GROUPS
            ):
                return f"{group.name} -> {group.now}"
    if from_config:
        for preferred in PRIMARY_GROUPS:
            if preferred in from_config:
                return f"{preferred} -> {from_config[preferred]}"
        for group, node in from_config.items():
            if group not in AUTO_GROUPS:
                return f"{group} -> {node}"
        group, node = next(iter(from_config.items()))
        return f"{group} -> {node}"
    return "No node selected"


class ClashTXController:
    def __init__(self, store: ConfigStore | None = None) -> None:
        self.store = store or ConfigStore()
        self.core = CoreManager(self.store)
        self.service = ServiceManager(self.store, self.core)
        self.subscription = SubscriptionManager(self.store)
        self.proxy = ProxyManager(self.store)
        self.tun = TunManager(self.store)
        self.network = NetworkManager(
            self.store, self.proxy, self.tun, self.subscription
        )
        self.api = MihomoAPI(self.store)
        self._test_all_lock = threading.Lock()
        self._test_all = TestAllProgress()

    def dashboard(self) -> dict[str, Any]:
        status = self.service.status()
        config = self.store.load_config()
        groups: list[ProxyGroup] = []
        if status.active:
            try:
                groups = self.api.groups()
            except Exception:
                groups = []
        return {
            "active": status.active,
            "installed": status.installed,
            "mode": config.proxy_mode,
            "proxy_host": config.system_proxy_host,
            "proxy_port": config.mixed_port,
            "network_mode": config.network_mode,
            "subscription": config.active_subscription,
            "node": pick_primary_node(
                groups,
                from_config=config.selected_nodes,
                preferred_group=config.active_node_group,
            ),
            "core_version": self.core.version(),
        }

    def traffic(self) -> dict[str, int]:
        try:
            up, down = self.api.traffic_sample()
        except Exception:
            return {"up": 0, "down": 0}
        return {"up": up, "down": down}

    def service_action(self, action: str) -> str:
        if action not in {"start", "stop", "restart"}:
            raise ValueError(f"Unknown service action: {action}")
        return getattr(self.service, action)()

    def list_subscriptions(self) -> list[dict[str, Any]]:
        config = self.store.load_config()
        return [
            {
                "name": item.name,
                "url": item.url,
                "updated_at": item.updated_at,
                "active": item.name == config.active_subscription,
            }
            for item in config.subscriptions
        ]

    def save_subscription(self, name: str, url: str) -> dict[str, Any]:
        subscription = self.subscription.add_or_update(name, url)
        reload_message = self._reload_config_message()
        return {"name": subscription.name, "message": reload_message}

    def activate_subscription(self, name: str) -> dict[str, str]:
        subscription = self.subscription.activate(name)
        return {"name": subscription.name, "message": self._reload_config_message()}

    def refresh_subscription(self, name: str) -> dict[str, str]:
        subscription = self.subscription.update(name)
        return {"name": subscription.name, "message": self._reload_config_message()}

    def refresh_all_subscriptions(
        self,
        progress: Callable[[int, int, str, str | None], None] | None = None,
    ) -> dict[str, Any]:
        config = self.store.load_config()
        successful: list[str] = []
        failed: list[dict[str, str]] = []
        subscriptions = list(config.subscriptions)
        total = len(subscriptions)
        for index, item in enumerate(subscriptions, start=1):
            if progress:
                progress(index, total, item.name, None)
            try:
                subscription = self.subscription.update(item.name)
                successful.append(subscription.name)
            except Exception as exc:
                failed.append({"name": item.name, "error": str(exc)})
                if progress:
                    progress(index, total, item.name, str(exc))
            else:
                if progress:
                    progress(index, total, item.name, "")

        reload_message = self._reload_config_message() if successful else "No subscriptions updated."
        return {
            "successful": successful,
            "failed": failed,
            "success_count": len(successful),
            "failure_count": len(failed),
            "message": reload_message,
        }

    def delete_subscription(self, name: str) -> dict[str, str]:
        self.subscription.delete(name)
        return {"message": self._reload_config_message()}

    def list_nodes(self) -> dict[str, Any]:
        config = self.store.load_config()
        state = self.store.load_state()
        groups = sort_proxy_groups(self.api.groups())
        group_entries: list[dict[str, Any]] = []
        rows: list[dict[str, Any]] = []
        for group in groups:
            nodes = build_group_nodes(
                group,
                sort_mode=config.sort_mode,
                latency_ms=state.last_latency_ms,
            )
            entry = {
                "name": group.name,
                "type": group.type,
                "now": group.now,
                "selectable": is_selectable_group(group),
                "nodes": nodes,
            }
            group_entries.append(entry)
            for node_entry in nodes:
                rows.append(
                    {
                        "group": group.name,
                        **node_entry,
                        "type": group.type,
                    }
                )
        active_group = pick_active_node_group(
            group_entries, config.active_node_group
        )
        return {
            "mode": config.proxy_mode,
            "sort_mode": config.sort_mode,
            "active_group": active_group,
            "groups": group_entries,
            "rows": rows,
        }

    def set_active_node_group(self, group_name: str) -> None:
        config = self.store.load_config()
        config.active_node_group = group_name
        self.store.save_config(config)

    def set_mode(self, mode: str) -> None:
        self.api.set_mode(mode)

    def set_sort_mode(self, sort_mode: str) -> None:
        config = self.store.load_config()
        config.sort_mode = sort_mode
        self.store.save_config(config)

    def select_node(self, group: str, node: str) -> list[str]:
        groups = {item.name: item for item in self.api.groups()}
        target = groups.get(group)
        if target is None:
            raise ValueError(f"Unknown group: {group}")
        if group in AUTO_GROUPS:
            raise ValueError(
                f"{group} is automatic; select a node under GLOBAL or selector group."
            )
        if not is_selectable_group(target):
            raise ValueError(
                f"{group} is {target.type}; only Selector groups support manual selection."
            )
        if node not in target.all:
            raise ValueError(f"{node} is not available in {group}.")
        if not is_proxy_node(node):
            raise ValueError(f"{node} is not a real proxy node.")

        updated: list[str] = []
        for synced_group in groups_to_sync(groups, group, node):
            self.api.select_node(synced_group, node)
            updated.append(synced_group)
        return updated

    def test_node(self, node: str) -> int:
        return self.api.delay(node)

    def test_all_nodes(
        self,
        *,
        progress: ProgressCallback | None = None,
        max_workers: int = DEFAULT_TEST_ALL_WORKERS,
        timeout_ms: int = 3000,
    ) -> dict[str, Any]:
        groups = self.api.groups()
        nodes = collect_testable_nodes(groups)
        total = len(nodes)
        if progress:
            progress(0, total, None)

        results: list[tuple[int, str]] = []
        latencies: dict[str, int] = {}
        completed = 0
        workers = max(1, min(max_workers, total or 1))

        def test_one(node: str) -> tuple[str, int | None]:
            try:
                delay = self.api.delay(node, timeout_ms=timeout_ms, persist=False)
            except Exception:
                return node, None
            if delay < 0:
                return node, None
            return node, delay

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(test_one, node): node for node in nodes}
            for future in as_completed(futures):
                node_name = futures[future]
                completed += 1
                try:
                    node, delay = future.result()
                    if delay is not None:
                        results.append((delay, node))
                        latencies[node] = delay
                except Exception:
                    pass
                if progress:
                    progress(completed, total, node_name)

        if latencies:
            state = self.store.load_state()
            state.last_latency_ms.update(latencies)
            self.store.save_state(state)

        fastest = None
        fastest_delay = None
        if results:
            fastest_delay, fastest = min(results, key=lambda item: item[0])
        return {
            "tested": len(results),
            "failed": total - len(results),
            "total": total,
            "fastest": fastest,
            "fastest_delay": fastest_delay,
        }

    def start_test_all_async(
        self,
        *,
        max_workers: int = DEFAULT_TEST_ALL_WORKERS,
        timeout_ms: int = 3000,
    ) -> None:
        with self._test_all_lock:
            if self._test_all.running:
                raise RuntimeError("Latency test already in progress")
            self._test_all = TestAllProgress(running=True)
        thread = threading.Thread(
            target=self._run_test_all_async,
            kwargs={"max_workers": max_workers, "timeout_ms": timeout_ms},
            daemon=True,
        )
        thread.start()

    def test_all_progress(self) -> dict[str, Any]:
        with self._test_all_lock:
            return asdict(self._test_all)

    def _run_test_all_async(self, *, max_workers: int, timeout_ms: int) -> None:
        def progress(done: int, total: int, node: str | None) -> None:
            with self._test_all_lock:
                self._test_all.done = done
                self._test_all.total = total
                self._test_all.current = node

        try:
            result = self.test_all_nodes(
                progress=progress,
                max_workers=max_workers,
                timeout_ms=timeout_ms,
            )
            with self._test_all_lock:
                self._test_all.result = result
        except Exception as exc:
            with self._test_all_lock:
                self._test_all.error = str(exc)
        finally:
            with self._test_all_lock:
                self._test_all.running = False

    def network_status(self) -> dict[str, Any]:
        config = self.store.load_config()
        proxy = self.proxy_status()
        tun_status = self.tun.status()
        caps_ready = core_has_tun_capabilities(self.core.binary_path)
        tun_message = tun_status.message
        if not caps_ready:
            tun_message = (
                f"{tun_message} Grant CAP_NET_ADMIN: {grant_caps_command(self.core.binary_path)}"
            )
        return {
            "mode": config.network_mode,
            "system_proxy_allowed": config.network_mode != "tun",
            "proxy": proxy,
            "tun": {
                "enabled": tun_status.enabled,
                "device_available": tun_status.device_available,
                "capabilities_ready": caps_ready,
                "tools_dir": str(tun_status.tools_dir),
                "ensure_script": str(tun_status.ensure_script),
                "stack": tun_status.stack,
                "message": tun_message,
            },
        }

    def set_network_mode(self, mode: str) -> str:
        if mode == "tun":
            try:
                self.core.ensure_tun_capabilities()
            except RuntimeError as exc:
                raise RuntimeError(str(exc)) from exc
        try:
            message = self.network.set_mode(mode)  # type: ignore[arg-type]
        except NetworkModeError as exc:
            raise RuntimeError(str(exc)) from exc
        reload_message = self._apply_network_mode_runtime()
        return f"{message} {reload_message}"

    def _apply_network_mode_runtime(self) -> str:
        if not self.service.status().active:
            return "Start Mihomo to apply network mode."
        try:
            self.service.restart()
            return "Mihomo restarted to apply network mode."
        except Exception as exc:
            return f"Config saved, restart failed: {exc}"

    def proxy_status(self) -> dict[str, Any]:
        status = self.proxy.status()
        payload = asdict(status)
        payload["env_file"] = str(status.env_file)
        return payload

    def apply_proxy(self, host: str, port: int, no_proxy: str) -> None:
        try:
            self.network.ensure_proxy_allowed()
        except NetworkModeError as exc:
            raise RuntimeError(str(exc)) from exc
        self.proxy.apply_settings(host, port, no_proxy)
        self.subscription.generate_runtime_config()
        if self.service.status().active:
            try:
                self.api.reload_config()
            except Exception:
                pass

    def enable_proxy(self) -> str:
        try:
            self.network.ensure_proxy_allowed()
        except NetworkModeError as exc:
            raise RuntimeError(str(exc)) from exc
        path = self.proxy.enable()
        message = f"System proxy enabled. Source: source {path}"
        if not self.proxy.port_open():
            message += " | Mihomo port is not listening yet"
        return message

    def disable_proxy(self) -> str:
        self.proxy.disable()
        return "System proxy disabled."

    def _reload_config_message(self) -> str:
        try:
            self.api.reload_config()
            return "Mihomo config reloaded."
        except Exception as exc:
            return f"Config saved, reload failed: {exc}"
