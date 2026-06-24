from __future__ import annotations

import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path

from clashtx.config import ConfigStore


@dataclass(frozen=True, slots=True)
class ProxyStatus:
    enabled: bool
    host: str
    port: int
    no_proxy: str
    env_file: Path
    env_exists: bool
    gnome_mode: str | None
    port_listening: bool


class ProxyManager:
    def __init__(self, store: ConfigStore | None = None) -> None:
        self.store = store or ConfigStore()

    @property
    def env_file(self) -> Path:
        return self.store.paths.config_dir / "proxy.env"

    def status(self) -> ProxyStatus:
        config = self.store.load_config()
        return ProxyStatus(
            enabled=config.system_proxy_enabled,
            host=config.system_proxy_host,
            port=config.mixed_port,
            no_proxy=config.system_proxy_no_proxy,
            env_file=self.env_file,
            env_exists=self.env_file.exists(),
            gnome_mode=_gnome_proxy_mode(),
            port_listening=self.port_open(config.mixed_port),
        )

    def apply_settings(self, host: str, port: int, no_proxy: str) -> None:
        config = self.store.load_config()
        if config.network_mode == "tun" or config.tun_enabled:
            raise RuntimeError(
                "TUN mode is active. Run 'clashtx mode system' before changing system proxy."
            )
        config.system_proxy_host = host.strip() or "127.0.0.1"
        config.mixed_port = port
        config.system_proxy_no_proxy = no_proxy.strip() or "localhost,127.0.0.1"
        self.store.save_config(config)
        if config.system_proxy_enabled:
            self.enable()

    def enable(self) -> Path:
        config = self.store.load_config()
        if config.network_mode == "tun" or config.tun_enabled:
            raise RuntimeError(
                "TUN mode is active. Run 'clashtx mode system' before enabling system proxy."
            )
        host = config.system_proxy_host
        port = config.mixed_port
        no_proxy = config.system_proxy_no_proxy
        proxy_url = f"http://{host}:{port}"
        socks_url = f"socks5://{host}:{port}"
        self.env_file.write_text(
            "\n".join(
                [
                    f"export http_proxy={proxy_url}",
                    f"export https_proxy={proxy_url}",
                    f"export all_proxy={socks_url}",
                    f"export HTTP_PROXY={proxy_url}",
                    f"export HTTPS_PROXY={proxy_url}",
                    f"export ALL_PROXY={socks_url}",
                    f"export no_proxy={no_proxy}",
                    f"export NO_PROXY={no_proxy}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        _set_gnome_proxy(host, port)
        config.system_proxy_enabled = True
        self.store.save_config(config)
        return self.env_file

    def port_open(self, port: int | None = None) -> bool:
        config = self.store.load_config()
        target_port = port if port is not None else config.mixed_port
        host = config.system_proxy_host
        with socket.socket() as sock:
            sock.settimeout(1)
            try:
                sock.connect((host, target_port))
            except OSError:
                return False
        return True

    def disable(self) -> None:
        config = self.store.load_config()
        config.system_proxy_enabled = False
        self.store.save_config(config)
        if self.env_file.exists():
            self.env_file.unlink()
        _unset_gnome_proxy()


def _gnome_proxy_mode() -> str | None:
    try:
        completed = subprocess.run(
            ["gsettings", "get", "org.gnome.system.proxy", "mode"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip().strip("'")


def _set_gnome_proxy(host: str, port: int) -> None:
    commands = [
        ["gsettings", "set", "org.gnome.system.proxy", "mode", "manual"],
        ["gsettings", "set", "org.gnome.system.proxy.http", "host", host],
        ["gsettings", "set", "org.gnome.system.proxy.http", "port", str(port)],
        ["gsettings", "set", "org.gnome.system.proxy.https", "host", host],
        ["gsettings", "set", "org.gnome.system.proxy.https", "port", str(port)],
        ["gsettings", "set", "org.gnome.system.proxy.socks", "host", host],
        ["gsettings", "set", "org.gnome.system.proxy.socks", "port", str(port)],
    ]
    for command in commands:
        subprocess.run(command, check=False, capture_output=True, text=True)


def _unset_gnome_proxy() -> None:
    subprocess.run(
        ["gsettings", "set", "org.gnome.system.proxy", "mode", "none"],
        check=False,
        capture_output=True,
        text=True,
    )
