from __future__ import annotations

from typing import Literal

from clashtx.config import ConfigStore
from clashtx.subscription import SubscriptionManager
from clashtx.system.proxy import ProxyManager
from clashtx.system.tun import TunManager

NetworkMode = Literal["system", "tun"]


class NetworkModeError(RuntimeError):
    pass


class NetworkManager:
    def __init__(
        self,
        store: ConfigStore | None = None,
        proxy: ProxyManager | None = None,
        tun: TunManager | None = None,
        subscription: SubscriptionManager | None = None,
    ) -> None:
        self.store = store or ConfigStore()
        self.proxy = proxy or ProxyManager(self.store)
        self.tun = tun or TunManager(self.store)
        self.subscription = subscription or SubscriptionManager(self.store)

    def current_mode(self) -> NetworkMode:
        config = self.store.load_config()
        if config.network_mode in {"system", "tun"}:
            return config.network_mode
        return "tun" if config.tun_enabled else "system"

    def set_mode(self, mode: NetworkMode) -> str:
        if mode == "tun":
            return self._enable_tun()
        if mode == "system":
            return self._enable_system()
        raise NetworkModeError(f"Unknown network mode: {mode}")

    def ensure_proxy_allowed(self) -> None:
        if self.current_mode() == "tun":
            raise NetworkModeError(
                "TUN mode is active. Run 'clashtx mode system' before enabling system proxy."
            )

    def _enable_tun(self) -> str:
        self.proxy.disable()
        self.tun.ensure_environment()
        if not self.tun.device_available():
            raise NetworkModeError(self.tun.status().message)
        self.tun.set_enabled(True)
        self.subscription.generate_runtime_config()
        return "TUN mode enabled. System proxy disabled."

    def _enable_system(self) -> str:
        self.tun.set_enabled(False)
        self.subscription.generate_runtime_config()
        env_path = self.proxy.enable()
        return (
            "System mode enabled. TUN disabled. "
            f"System proxy enabled. Source: source {env_path}"
        )
