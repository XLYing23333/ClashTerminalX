from __future__ import annotations

import os
import signal
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from clashtx.config import ConfigStore
from clashtx.core import CoreManager, ensure_geodata

SERVICE_NAME = "clashtx.service"


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    installed: bool
    enabled: bool
    active: bool
    text: str


class ServiceManager:
    def __init__(
        self,
        store: ConfigStore | None = None,
        core: CoreManager | None = None,
    ) -> None:
        self.store = store or ConfigStore()
        self.core = core or CoreManager(self.store)

    @property
    def service_path(self) -> Path:
        return Path.home() / ".config" / "systemd" / "user" / SERVICE_NAME

    def install(self) -> Path:
        if not self.core.exists():
            raise RuntimeError(f"Mihomo core is missing: {self.core.binary_path}")
        self.ensure_runtime_config()
        self.service_path.parent.mkdir(parents=True, exist_ok=True)
        self.service_path.write_text(self._unit_text(), encoding="utf-8")
        if _systemd_available():
            _systemctl("daemon-reload")
        return self.service_path

    def start(self) -> str:
        self.start_direct()
        return "ClashTX core started in direct process mode."

    def start_direct(self) -> int:
        if self.is_direct_active():
            return self._read_pid() or 0
        if not self.core.exists():
            raise RuntimeError(f"Mihomo core is missing: {self.core.binary_path}")
        self.ensure_runtime_config()
        log_file = self.store.paths.logs_dir / "mihomo.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_file.open("ab")
        process = subprocess.Popen(
            self.core.build_command(),
            stdout=log_handle,
            stderr=log_handle,
            start_new_session=True,
        )
        self.store.paths.pid_file.write_text(str(process.pid), encoding="utf-8")
        if not self.wait_until_ready(timeout=8):
            raise RuntimeError(
                f"Mihomo started with pid {process.pid}, but API did not become ready. "
                f"Check log: {log_file}"
            )
        return process.pid

    def ensure_runtime_config(self) -> None:
        ensure_geodata(self.store.paths.config_dir)
        try:
            from clashtx.subscription import SubscriptionManager

            SubscriptionManager(self.store).generate_runtime_config()
        except Exception:
            if not self.store.paths.generated_config.exists():
                self.store.write_generated_config(_base_mihomo_config(self.store.load_config()))

    def wait_until_ready(self, timeout: float = 5) -> bool:
        host, port = _split_host_port(self.store.load_config().external_controller)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.is_direct_active():
                return False
            try:
                with socket.create_connection((host, port), timeout=0.5):
                    return True
            except OSError:
                time.sleep(0.2)
        return False

    def stop_direct(self) -> bool:
        pids = self._managed_pids()
        pid = self._read_pid()
        if pid and pid not in pids:
            pids.append(pid)
        if not pids:
            self._clear_pid()
            return False
        stopped = False
        for pid in pids:
            stopped = self._terminate_pid(pid) or stopped
        self._clear_pid()
        return stopped

    def _terminate_pid(self, pid: int) -> bool:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return False
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if not _pid_alive(pid):
                return True
            time.sleep(0.2)
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return True

    def is_direct_active(self) -> bool:
        pids = self._managed_pids()
        if pids:
            self.store.paths.pid_file.write_text(str(pids[0]), encoding="utf-8")
            return True
        pid = self._read_pid()
        if pid and _pid_alive(pid):
            return True
        self._clear_pid()
        return False

    def _managed_pids(self) -> list[int]:
        pids: list[int] = []
        config_dir = str(self.store.paths.generated_config.parent)
        config_file = str(self.store.paths.generated_config)
        for proc_dir in Path("/proc").iterdir():
            if not proc_dir.name.isdigit():
                continue
            try:
                raw = (proc_dir / "cmdline").read_bytes()
            except OSError:
                continue
            if not raw:
                continue
            parts = [part.decode("utf-8", "ignore") for part in raw.split(b"\0") if part]
            if not parts:
                continue
            if config_dir in parts or config_file in parts:
                pids.append(int(proc_dir.name))
        return pids

    def _read_pid(self) -> int | None:
        try:
            return int(self.store.paths.pid_file.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None

    def _clear_pid(self) -> None:
        try:
            self.store.paths.pid_file.unlink()
        except FileNotFoundError:
            pass

    def stop(self) -> str:
        stopped = self.stop_direct()
        return "ClashTX core stopped." if stopped else "ClashTX core was not running."

    def restart(self) -> str:
        self.stop_direct()
        self.start_direct()
        return "ClashTX core restarted in direct process mode."

    def status(self) -> ServiceStatus:
        active = self.is_direct_active()
        pid = self._read_pid()
        text = (
            f"Direct process mode. PID: {pid}. "
            f"Core: {self.core.binary_path}. "
            f"API: {self.store.load_config().external_controller}. "
            f"Log: {self.store.paths.logs_dir / 'mihomo.log'}"
        )
        return ServiceStatus(
            installed=self.core.exists(),
            enabled=False,
            active=active,
            text=text,
        )

    def _unit_text(self) -> str:
        command = " ".join(_quote(part) for part in self.core.build_command())
        log_file = self.store.paths.logs_dir / "mihomo.log"
        return f"""[Unit]
Description=ClashTX Mihomo Core
After=network-online.target

[Service]
Type=simple
ExecStart={command}
Restart=on-failure
RestartSec=3
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
StandardOutput=append:{log_file}
StandardError=append:{log_file}

[Install]
WantedBy=default.target
"""

    def _legacy_start(self) -> str:
        if not self.service_path.exists():
            self.install()
        _systemctl("start", SERVICE_NAME)
        return "ClashTX service started."


def _systemctl(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["systemctl", "--user", *args],
        check=check,
        capture_output=True,
        text=True,
    )


def _systemd_available() -> bool:
    try:
        completed = _systemctl("show-environment", check=False)
    except FileNotFoundError:
        return False
    return completed.returncode == 0


def _quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def _base_mihomo_config(config) -> dict:
    return {
        "mixed-port": config.mixed_port,
        "allow-lan": False,
        "mode": {"rule": "rule", "global": "global", "direct": "direct"}[config.proxy_mode],
        "log-level": "info",
        "geo-auto-update": False,
        "external-controller": config.external_controller,
        "secret": config.secret,
        "tun": {
            "enable": config.tun_enabled,
            "stack": "system",
            "auto-route": True,
            "auto-detect-interface": True,
        },
    }


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _split_host_port(value: str) -> tuple[str, int]:
    host, _, port = value.rpartition(":")
    if not host or not port:
        return "127.0.0.1", 9090
    return host, int(port)
