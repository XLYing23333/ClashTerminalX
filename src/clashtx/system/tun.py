from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from clashtx.config import ConfigStore

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BUNDLED_TUN_DIR = PROJECT_ROOT / "vendor" / "tun"
ENSURE_TUN_SCRIPT = BUNDLED_TUN_DIR / "ensure-tun.sh"


@dataclass(frozen=True, slots=True)
class TunStatus:
    enabled: bool
    device_available: bool
    tools_dir: Path
    ensure_script: Path
    stack: str
    message: str


class TunManager:
    def __init__(self, store: ConfigStore | None = None) -> None:
        self.store = store or ConfigStore()

    @property
    def tools_dir(self) -> Path:
        override = os.environ.get("CLASHTX_TUN_DIR")
        if override:
            return Path(override).expanduser()
        return BUNDLED_TUN_DIR

    @property
    def ensure_script(self) -> Path:
        return self.tools_dir / "ensure-tun.sh"

    def device_available(self) -> bool:
        return Path("/dev/net/tun").exists()

    def ensure_environment(self) -> None:
        script = self.ensure_script
        if not script.exists():
            if not self.device_available():
                raise RuntimeError(
                    f"TUN device is unavailable and bundled script is missing: {script}"
                )
            return
        if not os.access(script, os.X_OK):
            script.chmod(script.stat().st_mode | 0o111)
        completed = subprocess.run(
            [str(script)],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(detail or "Failed to prepare TUN environment.")
        if not self.device_available():
            raise RuntimeError("TUN device is still unavailable after setup.")

    def status(self) -> TunStatus:
        config = self.store.load_config()
        if self.device_available():
            message = "TUN device is available."
        elif self.ensure_script.exists():
            message = "TUN device unavailable. Run ensure-tun.sh or load the tun module."
        else:
            message = "TUN device unavailable."
        return TunStatus(
            enabled=config.tun_enabled,
            device_available=self.device_available(),
            tools_dir=self.tools_dir,
            ensure_script=self.ensure_script,
            stack="system",
            message=message,
        )

    def set_enabled(self, enabled: bool) -> bool:
        config = self.store.load_config()
        config.tun_enabled = enabled
        config.network_mode = "tun" if enabled else "system"
        if enabled:
            config.system_proxy_enabled = False
        self.store.save_config(config)
        return self.device_available()
