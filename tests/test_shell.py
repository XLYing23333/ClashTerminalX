import os
import shutil
import pytest
import subprocess
from pathlib import Path

from clashtx.config import AppConfig
from clashtx.system.proxy import ProxyManager

# Restore only these two calls for a fresh, isolated Bash (never a proxy/core).
_REAL_RUN = subprocess.run
_REAL_POPEN = subprocess.Popen


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_source_keeps_shell_alive_and_does_not_execute_proxy_values(store, monkeypatch, tmp_path, shell):
    if not shutil.which(shell):
        pytest.skip(f"{shell} is not installed")
    marker = tmp_path / 'must-not-exist'
    payload = f"localhost; $(touch {marker}) 'literal'"
    store.save_config(AppConfig(system_proxy_no_proxy=payload))
    ProxyManager(store).enable()
    script = Path(__file__).resolve().parents[1] / 'clashtx.sh'
    monkeypatch.setattr(subprocess, 'Popen', _REAL_POPEN)
    command = 'before=$(set +o); source "$1" source; after=$(set +o); [[ "$before" == "$after" ]] || exit 9; printf "VALUE:%s\\nSURVIVED\\n" "$no_proxy"'
    options = ['--noprofile', '--norc'] if shell == 'bash' else ['-f']
    result = _REAL_RUN([shell, *options, '-c', command, shell, str(script)],
                       env=dict(os.environ), capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert 'SURVIVED' in result.stdout
    assert f'VALUE:{payload}' in result.stdout
    assert not marker.exists()
