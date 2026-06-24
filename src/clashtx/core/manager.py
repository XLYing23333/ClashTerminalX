from __future__ import annotations

import os
import subprocess
from pathlib import Path

from clashtx.config import AppConfig, ConfigStore

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BUNDLED_VERGE_CORE_PATH = PROJECT_ROOT / "vendor" / "mihomo" / "verge-mihomo"
BUNDLED_CORE_PATH = PROJECT_ROOT / "vendor" / "mihomo" / "mihomo"


class CoreManager:
    def __init__(self, store: ConfigStore | None = None) -> None:
        self.store = store or ConfigStore()

    @property
    def binary_path(self) -> Path:
        override = os.environ.get("CLASHTX_CORE_PATH")
        if override:
            return Path(override).expanduser()
        if BUNDLED_VERGE_CORE_PATH.exists() and os.access(BUNDLED_VERGE_CORE_PATH, os.X_OK):
            return BUNDLED_VERGE_CORE_PATH
        return BUNDLED_CORE_PATH

    def exists(self) -> bool:
        return self.binary_path.exists() and os.access(self.binary_path, os.X_OK)

    def version(self) -> str | None:
        if not self.exists():
            return None
        try:
            completed = subprocess.run(
                [str(self.binary_path), "-v"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        output = (completed.stdout or completed.stderr).strip()
        return output.splitlines()[0] if output else None

    def build_command(self, config: AppConfig | None = None) -> list[str]:
        app_config = config or self.store.load_config()
        config_path = self.store.paths.generated_config
        command = [
            str(self.binary_path),
            "-d",
            str(config_path.parent),
            "-f",
            str(config_path),
            "-ext-ctl",
            app_config.external_controller,
        ]
        if app_config.secret:
            command.extend(["-secret", app_config.secret])
        return command

    def ensure_tun_capabilities(self) -> None:
        from clashtx.system.capabilities import ensure_core_capabilities

        ensure_core_capabilities(self.binary_path)
