from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from clashtx.config import ConfigStore


@dataclass(frozen=True, slots=True)
class ProxyNode:
    name: str
    type: str
    udp: bool | None = None
    history: list[dict[str, Any]] | None = None


@dataclass(frozen=True, slots=True)
class ProxyGroup:
    name: str
    type: str
    now: str | None
    all: list[str]


class MihomoAPI:
    def __init__(self, store: ConfigStore | None = None) -> None:
        self.store = store or ConfigStore()
        config = self.store.load_config()
        self.base_url = f"http://{config.external_controller}"
        self.secret = config.secret

    def health(self) -> bool:
        try:
            with self._client() as client:
                response = client.get("/")
            return response.status_code < 500
        except httpx.HTTPError:
            return False

    def get_mode(self) -> str:
        with self._client() as client:
            response = client.get("/configs")
        response.raise_for_status()
        return str(response.json().get("mode", "rule"))

    def set_mode(self, mode: str) -> None:
        with self._client() as client:
            response = client.patch("/configs", json={"mode": mode})
        response.raise_for_status()
        config = self.store.load_config()
        config.proxy_mode = {"rule": "rule", "global": "global", "direct": "direct"}.get(
            mode, "rule"
        )
        self.store.save_config(config)

    def proxies(self) -> dict[str, Any]:
        with self._client() as client:
            response = client.get("/proxies")
        response.raise_for_status()
        return response.json().get("proxies", {})

    def configs(self) -> dict[str, Any]:
        with self._client() as client:
            response = client.get("/configs")
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {}

    def reload_config(self, force: bool = True) -> None:
        path = str(self.store.paths.generated_config)
        with self._client() as client:
            response = client.put(
                "/configs",
                params={"force": str(force).lower()},
                json={"path": path},
            )
        response.raise_for_status()

    def groups(self) -> list[ProxyGroup]:
        groups: list[ProxyGroup] = []
        for name, raw in self.proxies().items():
            node_names = raw.get("all")
            if isinstance(node_names, list):
                groups.append(
                    ProxyGroup(
                        name=name,
                        type=str(raw.get("type", "")),
                        now=raw.get("now"),
                        all=[str(item) for item in node_names],
                    )
                )
        return groups

    def select_node(self, group: str, node: str) -> None:
        group_path = quote(group, safe="")
        with self._client() as client:
            response = client.put(f"/proxies/{group_path}", json={"name": node})
        _raise_for_status(response)
        config = self.store.load_config()
        config.selected_nodes[group] = node
        self.store.save_config(config)

    def delay(self, name: str, timeout_ms: int = 5000, *, persist: bool = True) -> int:
        node_path = quote(name, safe="")
        with self._client() as client:
            response = client.get(
                f"/proxies/{node_path}/delay",
                params={"timeout": timeout_ms, "url": "https://www.gstatic.com/generate_204"},
            )
        response.raise_for_status()
        delay = int(response.json().get("delay", -1))
        if persist:
            state = self.store.load_state()
            state.last_latency_ms[name] = delay
            self.store.save_state(state)
        return delay

    def traffic_sample(self) -> tuple[int, int]:
        with self._client(timeout=3) as client:
            with client.stream("GET", "/traffic") as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    return int(data.get("up", 0)), int(data.get("down", 0))
        return 0, 0

    def _client(self, timeout: float = 15) -> httpx.Client:
        headers = {}
        if self.secret:
            headers["Authorization"] = f"Bearer {self.secret}"
        return httpx.Client(base_url=self.base_url, headers=headers, timeout=timeout)


def _raise_for_status(response: httpx.Response) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = response.text.strip()
        if detail:
            raise RuntimeError(f"{response.status_code} {detail}") from exc
        raise
