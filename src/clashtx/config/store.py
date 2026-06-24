from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from .models import AppConfig, RuntimeState

APP_NAME = "clashtx"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROJECT_RUNTIME_DIR = PROJECT_ROOT / ".runtime"
_JSON_LOCK = threading.RLock()


@dataclass(frozen=True, slots=True)
class AppPaths:
    config_dir: Path
    data_dir: Path
    cache_dir: Path
    subscriptions_dir: Path
    generated_config: Path
    app_config: Path
    runtime_state: Path
    core_dir: Path
    logs_dir: Path
    pid_file: Path

    @classmethod
    def defaults(cls) -> "AppPaths":
        config_dir = Path(os.environ.get("CLASHTX_CONFIG_DIR", PROJECT_RUNTIME_DIR / "config"))
        data_dir = Path(os.environ.get("CLASHTX_DATA_DIR", PROJECT_RUNTIME_DIR / "data"))
        cache_dir = Path(os.environ.get("CLASHTX_CACHE_DIR", PROJECT_RUNTIME_DIR / "cache"))
        return cls(
            config_dir=config_dir,
            data_dir=data_dir,
            cache_dir=cache_dir,
            subscriptions_dir=config_dir / "subscriptions",
            generated_config=config_dir / "mihomo.yaml",
            app_config=config_dir / "config.json",
            runtime_state=config_dir / "state.json",
            core_dir=data_dir / "core",
            logs_dir=cache_dir / "logs",
            pid_file=cache_dir / "mihomo.pid",
        )

    def ensure(self) -> None:
        for directory in (
            self.config_dir,
            self.data_dir,
            self.cache_dir,
            self.subscriptions_dir,
            self.core_dir,
            self.logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


class ConfigStore:
    def __init__(self, paths: AppPaths | None = None) -> None:
        self.paths = paths or AppPaths.defaults()
        self.paths.ensure()

    def load_config(self) -> AppConfig:
        return AppConfig.from_dict(_read_json(self.paths.app_config))

    def save_config(self, config: AppConfig) -> None:
        _write_json(self.paths.app_config, config.to_dict())

    def load_state(self) -> RuntimeState:
        return RuntimeState.from_dict(_read_json(self.paths.runtime_state))

    def save_state(self, state: RuntimeState) -> None:
        _write_json(self.paths.runtime_state, state.to_dict())

    def read_generated_config(self) -> dict[str, Any]:
        if not self.paths.generated_config.exists():
            return {}
        try:
            import yaml
        except ModuleNotFoundError:
            return {}
        with self.paths.generated_config.open("r", encoding="utf-8") as file:
            value = yaml.safe_load(file) or {}
        return value if isinstance(value, dict) else {}

    def write_generated_config(self, data: dict[str, Any]) -> None:
        self.paths.generated_config.parent.mkdir(parents=True, exist_ok=True)
        with self.paths.generated_config.open("w", encoding="utf-8") as file:
            try:
                import yaml
            except ModuleNotFoundError:
                file.write(_simple_yaml_dump(data))
            else:
                yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with _JSON_LOCK:
        raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except JSONDecodeError:
        data = _recover_json_object(raw, path)
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    with _JSON_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        tmp_path.replace(path)


def _recover_json_object(raw: str, path: Path) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    try:
        data, end = decoder.raw_decode(raw)
    except JSONDecodeError:
        backup = path.with_suffix(path.suffix + ".broken")
        path.replace(backup)
        return {}
    if not isinstance(data, dict):
        return {}
    if raw[end:].strip():
        _write_json(path, data)
    return data


def _user_config_dir() -> str:
    try:
        from platformdirs import user_config_dir

        return user_config_dir(APP_NAME)
    except ModuleNotFoundError:
        return str(Path.home() / ".config" / APP_NAME)


def _user_data_dir() -> str:
    try:
        from platformdirs import user_data_dir

        return user_data_dir(APP_NAME)
    except ModuleNotFoundError:
        return str(Path.home() / ".local" / "share" / APP_NAME)


def _user_cache_dir() -> str:
    try:
        from platformdirs import user_cache_dir

        return user_cache_dir(APP_NAME)
    except ModuleNotFoundError:
        return str(Path.home() / ".cache" / APP_NAME)


def _simple_yaml_dump(data: dict[str, Any], indent: int = 0) -> str:
    lines: list[str] = []
    prefix = " " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_simple_yaml_dump(value, indent + 2).rstrip())
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
        elif value is None:
            lines.append(f"{prefix}{key}: null")
        elif isinstance(value, int | float):
            lines.append(f"{prefix}{key}: {value}")
        else:
            text = str(value).replace("'", "''")
            lines.append(f"{prefix}{key}: '{text}'")
    return "\n".join(lines) + "\n"
