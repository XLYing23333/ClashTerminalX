from __future__ import annotations

import importlib.util
import json
import re
import uuid
import warnings
from collections import Counter
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import Any

from clashtx.config import AppConfig, ConfigStore, Subscription
from clashtx.config.locking import config_transaction
from clashtx.config.store import atomic_write


class SubscriptionManager:
    def __init__(self, store: ConfigStore | None = None) -> None:
        self.store = store or ConfigStore()

    @config_transaction
    def add_or_update(self, name: str, url: str) -> Subscription:
        if not name.strip() or not url.strip():
            raise ValueError("Subscription name and URL are required.")
        config = self.store.load_config()
        self._migrate(config)
        existing = next((item for item in config.subscriptions if item.name == name), None)
        file_name = existing.file if existing else f"{uuid.uuid4().hex}.yaml"
        target = self._path(file_name)
        data = self.download(url)
        parsed = parse_subscription_yaml(data)
        atomic_write(target, data)

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

    @config_transaction
    def update(self, name: str) -> Subscription:
        config = self.store.load_config()
        self._migrate(config)
        current = self.get(config, name)
        data = self.download(current.url)
        parsed = parse_subscription_yaml(data)
        target = self._path(current.file)
        atomic_write(target, data)

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

    @config_transaction
    def activate(self, name: str) -> Subscription:
        config = self.store.load_config()
        self._migrate(config)
        subscription = self.get(config, name)
        config.active_subscription = subscription.name
        self.store.save_config(config)
        self.generate_runtime_config(config, subscription)
        return subscription

    @config_transaction
    def delete(self, name: str) -> None:
        config = self.store.load_config()
        self._migrate(config)
        subscription = self.get(config, name)
        config.subscriptions = [item for item in config.subscriptions if item.name != name]
        if config.active_subscription == name:
            config.active_subscription = None
        path = self._path(subscription.file)
        if path.exists():
            path.unlink()
        self.store.save_config(config)
        self.generate_runtime_config(config)

    def _path(self, filename: str) -> Path:
        if not filename or Path(filename).name != filename or not filename.endswith(".yaml"):
            raise ValueError("Invalid subscription file path.")
        path = self.store.paths.subscriptions_dir / filename
        if path.is_symlink():
            raise ValueError("Subscription files must not be symbolic links.")
        return path

    def _migrate(self, config: AppConfig) -> None:
        old = [item for item in config.subscriptions if not re.fullmatch(r"[0-9a-f]{32}\.yaml", item.file)]
        counts = Counter(item.file for item in config.subscriptions)
        shared = [item for item in config.subscriptions if counts[item.file] > 1]
        candidates = {id(item): item for item in old + shared}.values()
        candidates = list(candidates)
        original_files = {item.file for item in candidates}
        if not candidates:
            return
        backup = self.store.paths.config_dir / ("subscription-backup-" + uuid.uuid4().hex)
        backup.mkdir(mode=0o700)
        atomic_write(backup / "config.json", json.dumps(config.to_dict(), ensure_ascii=False, indent=2))
        for item in candidates:
            path = self._path(item.file)
            filename = f"{uuid.uuid4().hex}.yaml"
            if path.exists():
                content = path.read_text(encoding="utf-8")
                atomic_write(backup / item.file, content)
                atomic_write(self._path(filename), content)
            if counts[item.file] > 1:
                message = f"Subscription {item.name}: shared file migrated; refresh this subscription to restore provider content. Overwritten history cannot be recovered."
                config.migration_warnings.append(message)
                warnings.warn(message, UserWarning, stacklevel=2)
            item.file = filename
        self.store.save_config(config)
        for filename in original_files - {item.file for item in config.subscriptions}:
            self._path(filename).unlink(missing_ok=True)

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

    @config_transaction
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
            path = self._path(active.file)
            if path.exists() and not source:
                source = _read_yaml(path)

        source.update(
            {
                "mixed-port": app_config.mixed_port,
                "mode": app_config.proxy_mode,
                "geo-auto-update": False,
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
        source = self.apply_global_script(source)
        # Managed endpoint/auth/logging cannot be replaced by a subscription or script.
        source.update({"external-controller": app_config.external_controller,
                       "secret": app_config.secret, "log-level": "warning"})
        self.store.write_generated_config(source)
        return source

    def apply_global_script(self, config: dict[str, Any]) -> dict[str, Any]:
        script_path = self.store.paths.global_script
        if not script_path.exists():
            return config

        spec = importlib.util.spec_from_file_location(
            "clashtx_global_script",
            script_path,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load global script: {script_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        main = getattr(module, "main", None)
        if not callable(main):
            raise RuntimeError(
                f"Global script must define a callable main(config): {script_path}"
            )

        result = main(config)
        if result is None:
            return config
        if not isinstance(result, dict):
            raise RuntimeError("Global script main(config) must return a dict or None.")
        return result


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
