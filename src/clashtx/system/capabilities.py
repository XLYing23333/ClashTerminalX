from __future__ import annotations

import subprocess
from pathlib import Path

TUN_CAPS = "cap_net_admin,cap_net_bind_service+ep"


def core_has_tun_capabilities(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        completed = subprocess.run(
            ["getcap", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False
    return "cap_net_admin" in completed.stdout


def grant_caps_command(path: Path) -> str:
    return f"sudo setcap {TUN_CAPS} {path}"


def ensure_core_capabilities(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"Mihomo core not found: {path}")
    if core_has_tun_capabilities(path):
        return
    completed = subprocess.run(
        ["setcap", TUN_CAPS, str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0 and core_has_tun_capabilities(path):
        return
    raise RuntimeError(
        "TUN mode requires CAP_NET_ADMIN on the Mihomo binary. Run:\n"
        "  ./vendor/tun/grant-caps.sh\n"
        f"Or: {grant_caps_command(path)}"
    )
