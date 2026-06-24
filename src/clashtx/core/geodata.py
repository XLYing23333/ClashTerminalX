from __future__ import annotations

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BUNDLED_GEODATA_DIR = PROJECT_ROOT / "vendor" / "geodata"

GEODATA_FILES = (
    "geoip.metadb",
    "geosite.dat",
)


def ensure_geodata(config_dir: Path) -> list[Path]:
    """Copy bundled geodata into Mihomo's -d directory when missing or stale."""
    if not BUNDLED_GEODATA_DIR.is_dir():
        return []

    config_dir.mkdir(parents=True, exist_ok=True)
    installed: list[Path] = []
    for name in GEODATA_FILES:
        source = BUNDLED_GEODATA_DIR / name
        if not source.is_file():
            continue
        target = config_dir / name
        if _should_copy(source, target):
            shutil.copy2(source, target)
        installed.append(target)
    return installed


def _should_copy(source: Path, target: Path) -> bool:
    if not target.exists():
        return True
    return source.stat().st_mtime > target.stat().st_mtime
