from __future__ import annotations

import re
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import Any

from clashtx.config import AppConfig, ConfigStore, Subscription


class SubscriptionManager:
    def __init__(self, store: ConfigStore | None = None) -> None:
        self.store = store or ConfigStore()

    def add_or_update(self, name: str, url: str) -> Subscription:
        file_name = f"{_slug(name)}.yaml"
        target = self.store.paths.subscriptions_dir / file_name
        data = self.download(url)
        parsed = parse_subscription_yaml(data)
        target.write_text(data, encoding="utf-8")

        config = self.store.load_config()
        subscription = Subscription(
            name=name,
            url=url,
            file=file_name,
            updated_at=datetime.now(UTC).isoformat(),
        )
        config.subscriptions = [
            item for item in config.subscriptions if item.name != name
        ] + [subscription]
        self.store.save_config(config)
        if config.active_subscription == name:
            self.generate_runtime_config(config, subscription, parsed)
        else:
            self.generate_runtime_config(config)
        return subscription

    def update(self, name: str) -> Subscription:
        config = self.store.load_config()
        current = self.get(config, name)
        data = self.download(current.url)
        parsed = parse_subscription_yaml(data)
        target = self.store.paths.subscriptions_dir / current.file
        target.write_text(data, encoding="utf-8")

        updated = Subscription(
            name=current.name,
            url=current.url,
            file=current.file,
            updated_at=datetime.now(UTC).isoformat(),
        )
        config.subscriptions = [
            updated if item.name == updated.name else item for item in config.subscriptions
        ]
        self.store.save_config(config)
        if config.active_subscription == updated.name:
            self.generate_runtime_config(config, updated, parsed)
        return updated

    def activate(self, name: str) -> Subscription:
        config = self.store.load_config()
        subscription = self.get(config, name)
        config.active_subscription = subscription.name
        self.store.save_config(config)
        self.generate_runtime_config(config, subscription)
        return subscription

    def delete(self, name: str) -> None:
        config = self.store.load_config()
        subscription = self.get(config, name)
        config.subscriptions = [item for item in config.subscriptions if item.name != name]
        if config.active_subscription == name:
            config.active_subscription = None
        path = self.store.paths.subscriptions_dir / subscription.file
        if path.exists():
            path.unlink()
        self.store.save_config(config)
        self.generate_runtime_config(config)

    def get(self, config: AppConfig, name: str) -> Subscription:
        for subscription in config.subscriptions:
            if subscription.name == name:
                return subscription
        raise KeyError(f"Subscription not found: {name}")

    def active(self) -> Subscription | None:
        config = self.store.load_config()
        if not config.active_subscription:
            return None
        return self.get(config, config.active_subscription)

    def download(self, url: str) -> str:
        httpx = import_module("httpx")

        headers = {
            "User-Agent": "clash-verge/v2.2.3 mihomo",
            "Accept": "text/yaml, application/yaml, application/x-yaml, text/plain, */*",
        }
        with httpx.Client(follow_redirects=True, timeout=45) as client:
            response = client.get(url, headers=headers)
            if response.status_code == 403:
                raise RuntimeError(
                    "Subscription server returned 403 Forbidden. Check the URL, token, "
                    "or whether the provider blocks non-browser/server requests."
                )
            response.raise_for_status()
            return response.text

    def generate_runtime_config(
        self,
        config: AppConfig | None = None,
        subscription: Subscription | None = None,
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        app_config = config or self.store.load_config()
        active = subscription
        if active is None and app_config.active_subscription:
            active = self.get(app_config, app_config.active_subscription)

        source = source or {}
        if active:
            path = self.store.paths.subscriptions_dir / active.file
            if path.exists() and not source:
                source = _read_yaml(path)

        source.update(
            {
                "mixed-port": app_config.mixed_port,
                "mode": app_config.proxy_mode,
                "external-controller": app_config.external_controller,
                "secret": app_config.secret,
                "tun": {
                    **source.get("tun", {}),
                    "enable": app_config.tun_enabled,
                    "stack": source.get("tun", {}).get("stack", "system"),
                    "auto-route": source.get("tun", {}).get("auto-route", True),
                    "auto-detect-interface": source.get("tun", {}).get(
                        "auto-detect-interface", True
                    ),
                },
            }
        )
        self.store.write_generated_config(source)
        return source


def sort_nodes(nodes: list[str], mode: str, latency_ms: dict[str, int] | None = None) -> list[str]:
    latency = latency_ms or {}
    if mode == "a-z":
        return sorted(nodes, key=str.casefold)
    if mode == "z-a":
        return sorted(nodes, key=str.casefold, reverse=True)
    return sorted(nodes, key=lambda node: (latency.get(node, 10**9), node.casefold()))


def parse_subscription_yaml(raw: str) -> dict[str, Any]:
    yaml = import_module("yaml")

    if not raw.strip():
        raise ValueError("Downloaded subscription is empty.")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ValueError("Downloaded content is not valid YAML.") from exc
    if not isinstance(data, dict):
        raise ValueError("Downloaded content is not a YAML mapping.")
    if not any(key in data for key in ("proxies", "proxy-providers", "proxy-groups")):
        raise ValueError(
            "Downloaded YAML does not look like a Clash/Mihomo subscription "
            "(missing proxies, proxy-providers, or proxy-groups)."
        )
    return data


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return parse_subscription_yaml(file.read())


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip()).strip("-")
    return slug or "subscription"
