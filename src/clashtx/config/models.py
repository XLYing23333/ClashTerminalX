from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

ProxyMode = Literal["rule", "global", "direct"]
SortMode = Literal["latency", "a-z", "z-a"]
NetworkMode = Literal["system", "tun"]


@dataclass(slots=True)
class Subscription:
    name: str
    url: str
    file: str
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Subscription":
        return cls(
            name=str(raw.get("name", "")),
            url=str(raw.get("url", "")),
            file=str(raw.get("file", "")),
            updated_at=raw.get("updated_at"),
        )


@dataclass(slots=True)
class AppConfig:
    subscriptions: list[Subscription] = field(default_factory=list)
    active_subscription: str | None = None
    proxy_mode: ProxyMode = "rule"
    sort_mode: SortMode = "latency"
    selected_nodes: dict[str, str] = field(default_factory=dict)
    active_node_group: str | None = None
    system_proxy_enabled: bool = False
    system_proxy_host: str = "127.0.0.1"
    system_proxy_no_proxy: str = "localhost,127.0.0.1"
    network_mode: NetworkMode = "system"
    tun_enabled: bool = False
    mixed_port: int = 7897
    external_controller: str = "127.0.0.1:9090"
    secret: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AppConfig":
        subscriptions = [
            Subscription.from_dict(item)
            for item in raw.get("subscriptions", [])
            if isinstance(item, dict)
        ]
        network_mode = _network_mode(raw)
        return cls(
            subscriptions=subscriptions,
            active_subscription=raw.get("active_subscription"),
            proxy_mode=_mode(raw.get("proxy_mode")),
            sort_mode=_sort(raw.get("sort_mode")),
            selected_nodes=dict(raw.get("selected_nodes", {})),
            active_node_group=raw.get("active_node_group"),
            system_proxy_enabled=(
                False
                if network_mode == "tun"
                else bool(raw.get("system_proxy_enabled", False))
            ),
            system_proxy_host=str(raw.get("system_proxy_host", "127.0.0.1")),
            system_proxy_no_proxy=str(
                raw.get("system_proxy_no_proxy", "localhost,127.0.0.1")
            ),
            network_mode=network_mode,
            tun_enabled=network_mode == "tun",
            mixed_port=_mixed_port(raw.get("mixed_port")),
            external_controller=str(raw.get("external_controller", "127.0.0.1:9090")),
            secret=str(raw.get("secret", "")),
        )

    def __post_init__(self) -> None:
        if self.tun_enabled or self.network_mode == "tun":
            object.__setattr__(self, "network_mode", "tun")
            object.__setattr__(self, "tun_enabled", True)
            object.__setattr__(self, "system_proxy_enabled", False)
        else:
            object.__setattr__(self, "network_mode", "system")
            object.__setattr__(self, "tun_enabled", False)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RuntimeState:
    core_running: bool = False
    core_version: str | None = None
    last_error: str | None = None
    active_config: str | None = None
    last_latency_ms: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RuntimeState":
        return cls(
            core_running=bool(raw.get("core_running", False)),
            core_version=raw.get("core_version"),
            last_error=raw.get("last_error"),
            active_config=raw.get("active_config"),
            last_latency_ms={
                str(key): int(value)
                for key, value in raw.get("last_latency_ms", {}).items()
                if isinstance(value, int | float)
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _mode(value: Any) -> ProxyMode:
    if value in {"rule", "global", "direct"}:
        return value
    return "rule"


def _sort(value: Any) -> SortMode:
    if value in {"latency", "a-z", "z-a"}:
        return value
    return "latency"


def _mixed_port(value: Any) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        return 7897
    return port


def _network_mode(raw: dict[str, Any]) -> NetworkMode:
    mode = raw.get("network_mode")
    if mode in {"system", "tun"}:
        return mode
    if bool(raw.get("tun_enabled", False)):
        return "tun"
    return "system"
