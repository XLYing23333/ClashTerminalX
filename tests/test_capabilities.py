from pathlib import Path

import pytest

from clashtx.system.capabilities import (
    core_has_tun_capabilities,
    ensure_core_capabilities,
    grant_caps_command,
)


def test_core_has_tun_capabilities(tmp_path, monkeypatch):
    binary = tmp_path / "mihomo"
    binary.write_bytes(b"fake")

    def fake_run(args, **kwargs):
        class Result:
            returncode = 0
            stdout = f"{binary} cap_net_admin,cap_net_bind_service=ep"
            stderr = ""

        return Result()

    monkeypatch.setattr("clashtx.system.capabilities.subprocess.run", fake_run)
    assert core_has_tun_capabilities(binary) is True


def test_ensure_core_capabilities_raises_with_command(tmp_path, monkeypatch):
    binary = tmp_path / "mihomo"
    binary.write_bytes(b"fake")

    def fake_run(args, **kwargs):
        class Result:
            returncode = 1
            stdout = ""
            stderr = "Operation not permitted"

        return Result()

    monkeypatch.setattr("clashtx.system.capabilities.subprocess.run", fake_run)
    monkeypatch.setattr(
        "clashtx.system.capabilities.core_has_tun_capabilities", lambda _path: False
    )

    with pytest.raises(RuntimeError) as exc:
        ensure_core_capabilities(binary)

    assert grant_caps_command(binary) in str(exc.value)
