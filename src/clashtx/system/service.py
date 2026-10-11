from __future__ import annotations

import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from clashtx.config import ConfigStore
from clashtx.config.locking import file_lock
from clashtx.config.store import _write_json
from clashtx.core import CoreManager, ensure_geodata
from clashtx.system.process import controller_address, is_core, matches, owns_listener, process_identity, process_exists

SERVICE_NAME = 'clashtx.service'


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    installed: bool
    enabled: bool
    active: bool
    text: str


class ServiceManager:
    def __init__(self, store: ConfigStore | None = None, core: CoreManager | None = None):
        self.store = store or ConfigStore()
        self.core = core or CoreManager(self.store)

    @property
    def log_file(self) -> Path:
        return self.store.paths.logs_dir / 'mihomo.log'

    def _lock(self):
        return file_lock(self.store.paths.cache_dir / '.service.lock')

    def _record(self) -> dict | None:
        try:
            raw = self.store.paths.pid_file.read_text().strip()
        except FileNotFoundError:
            return None
        try:
            record = json.loads(raw)
        except ValueError as exc:
            raise RuntimeError('Invalid core identity file; refusing process operations.') from exc
        if type(record) is int:
            if record <= 1:
                raise RuntimeError("Invalid core PID; refusing process operations.")
            identity = process_identity(record)
            if identity is None:
                if process_exists(record):
                    raise RuntimeError("Legacy core identity cannot be read; refusing process operations.")
                return None
            if not is_core(identity, self.core.binary_path, self.store.paths.generated_config):
                raise RuntimeError('Legacy PID belongs to an unverified process; refusing to control it.')
            args = identity['args']
            try:
                if args.count('-ext-ctl') != 1:
                    raise ValueError('ambiguous controller')
                controller = args[args.index('-ext-ctl') + 1]
                controller_address(controller)
            except (ValueError, IndexError) as exc:
                raise RuntimeError('Legacy controller identity is invalid.') from exc
            return {'version': 1, 'core': identity, 'runner': None, 'controller': controller}
        if not isinstance(record, dict) or record.get('version') != 1 or not isinstance(record.get('core'), dict):
            raise RuntimeError('Invalid core identity record; refusing process operations.')
        for value in [record['core'], record.get('runner')]:
            if value is None:
                continue
            if (not isinstance(value, dict) or type(value.get('pid')) is not int or value['pid'] <= 1
                    or type(value.get('uid')) is not int or value['uid'] < 0
                    or not isinstance(value.get('start_time'), str) or not value['start_time'].isdigit()
                    or not isinstance(value.get('exe'), str) or not isinstance(value.get('args'), list)
                    or not all(isinstance(argument, str) for argument in value['args'])):
                raise RuntimeError('Invalid process identity fields; refusing process operations.')
        if not isinstance(record.get('controller'), str):
            raise RuntimeError('Invalid controller identity; refusing process operations.')
        return record

    def _verified_core(self, record: dict | None) -> bool:
        if not record:
            return False
        identity = record.get('core')
        return (matches(identity) and is_core(identity, self.core.binary_path,
                                             self.store.paths.generated_config, record.get('controller')))

    def is_direct_active(self) -> bool:
        try:
            return self._verified_core(self._record())
        except RuntimeError:
            return False

    def _verified_runner(self, identity: dict | None) -> bool:
        if not matches(identity) or identity['uid'] != os.getuid() or identity['exe'] != str(Path(sys.executable).resolve()):
            return False
        args = identity['args']
        try:
            return (args[args.index('-m') + 1] == 'clashtx.system.runner'
                    and args.count('--config-dir') == 1
                    and Path(args[args.index('--config-dir') + 1]).resolve() == self.store.paths.config_dir.resolve())
        except (ValueError, IndexError):
            return False

    def assert_api_owner(self) -> None:
        record = self._record()
        config = self.store.load_config()
        if not self._verified_core(record) or record['controller'] != config.external_controller:
            raise RuntimeError('No verified ClashTX core is running; refusing controller access.')
        if not owns_listener(record['core']['pid'], config.external_controller) or not self._verified_core(record):
            raise RuntimeError('Controller listener does not belong to the ClashTX core.')

    def ensure_runtime_config(self) -> None:
        from clashtx.subscription import SubscriptionManager
        with self.store.transaction():
            config = self.store.load_config()
            controller_address(config.external_controller)
            if not config.secret:
                config.secret = secrets.token_urlsafe(32)
                self.store.save_config(config)
            ensure_geodata(self.store.paths.config_dir)
            SubscriptionManager(self.store).generate_runtime_config(config)

    def _check_controller_free(self) -> None:
        host, port = controller_address(self.store.load_config().external_controller)
        try:
            with socket.socket(socket.AF_INET6 if ':' in host else socket.AF_INET) as sock:
                sock.bind((host, port))
        except OSError as exc:
            raise RuntimeError('Mihomo controller address is occupied or unavailable; existing services were not changed.') from exc

    def start_direct(self) -> int:
        with self._lock():
            record = self._record()
            if self._verified_core(record):
                return record['core']['pid']
            if record:
                # A live runner or a reused PID must never be overwritten or killed.
                if process_exists(record['core'].get('pid', 0)) or matches(record.get('runner')):
                    raise RuntimeError('Stored process identity is inconsistent; refusing to start another core.')
            if not self.core.exists():
                raise RuntimeError(f'Mihomo core is missing: {self.core.binary_path}')
            self._check_controller_free()
            self.ensure_runtime_config()
            self.store.paths.pid_file.unlink(missing_ok=True)
            env = os.environ.copy()
            env.update(CLASHTX_CONFIG_DIR=str(self.store.paths.config_dir.resolve()),
                       CLASHTX_DATA_DIR=str(self.store.paths.data_dir.resolve()),
                       CLASHTX_CACHE_DIR=str(self.store.paths.cache_dir.resolve()),
                       CLASHTX_CORE_PATH=str(self.core.binary_path.resolve()))
            source = str(Path(__file__).resolve().parents[2])
            env['PYTHONPATH'] = source + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
            runner = subprocess.Popen([sys.executable, '-m', 'clashtx.system.runner', '--config-dir', str(self.store.paths.config_dir.resolve())],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                      start_new_session=True, env=env)
            runner_identity = process_identity(runner.pid)
            if not self.wait_until_ready(timeout=8):
                try:
                    self.stop_direct()
                finally:
                    if matches(runner_identity):
                        self._terminate_identity(runner_identity)
                    try:
                        runner.wait(timeout=6)
                    except subprocess.TimeoutExpired:
                        pass
                raise RuntimeError(f'Mihomo failed to become ready; check log: {self.log_file}')
            return self._record()['core']['pid']

    def wait_until_ready(self, timeout: float = 5) -> bool:
        import httpx
        host, port = controller_address(self.store.load_config().external_controller)
        url_host = f'[{host}]' if ':' in host else host
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                self.assert_api_owner()
                with httpx.Client(trust_env=False, timeout=0.5) as client:
                    response = client.get(f'http://{url_host}:{port}/version',
                                          headers={'Authorization': 'Bearer ' + self.store.load_config().secret})
                if response.status_code == 200 and isinstance(response.json().get('version'), str):
                    self.assert_api_owner()
                    return True
            except (RuntimeError, OSError, ValueError, httpx.HTTPError):
                pass
            time.sleep(0.1)
        return False

    def _terminate_identity(self, identity: dict) -> bool:
        if not matches(identity):
            return False
        fd = None
        try:
            if hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal'):
                fd = os.pidfd_open(identity['pid'])
            if not matches(identity):
                return False
            def send(sig):
                if fd is not None:
                    signal.pidfd_send_signal(fd, sig)
                elif matches(identity):
                    os.kill(identity['pid'], sig)
            send(signal.SIGTERM)
            deadline = time.monotonic() + 7
            while time.monotonic() < deadline:
                if not matches(identity):
                    return True
                time.sleep(0.1)
            send(signal.SIGKILL)
            return True
        except ProcessLookupError:
            return False
        finally:
            if fd is not None:
                os.close(fd)

    def stop_direct(self) -> bool:
        with self._lock():
            record = self._record()
            if record is None:
                self.store.paths.pid_file.unlink(missing_ok=True)
                return False
            core_live = process_identity(record['core'].get('pid', 0))
            if core_live is None and process_exists(record['core'].get('pid', 0)):
                raise RuntimeError("Core identity cannot be read; refusing process operations.")
            if core_live and not self._verified_core(record):
                raise RuntimeError('Core PID was reused or identity changed; refusing to terminate it.')
            runner = record.get('runner')
            if runner and process_exists(runner.get('pid', 0)) and not self._verified_runner(runner):
                raise RuntimeError('Runner identity changed; refusing to terminate it.')
            stopped = False
            if self._verified_runner(runner):
                stopped = self._terminate_identity(runner)
            if self._verified_core(record):
                stopped = self._terminate_identity(record['core']) or stopped
            self.store.paths.pid_file.unlink(missing_ok=True)
            return stopped

    def start(self) -> str:
        self.start_direct()
        return 'ClashTX core started with bounded background logging.'

    def stop(self) -> str:
        return 'ClashTX core stopped.' if self.stop_direct() else 'ClashTX core was not running.'

    def restart(self) -> str:
        with self._lock():
            self.stop_direct()
            self.start_direct()
        return 'ClashTX core restarted with bounded background logging.'

    def status(self) -> ServiceStatus:
        active = self.is_direct_active()
        try:
            record = self._record()
            text = f"Verified process mode. PID: {record['core']['pid'] if active else 'none'}. Log: {self.log_file}"
            if active and not record.get('runner'):
                text += ' | Legacy core: restart explicitly to enable bounded logging.'
        except RuntimeError as exc:
            text = str(exc)
        return ServiceStatus(self.core.exists(), False, active, text)
