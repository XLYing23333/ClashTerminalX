from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import HTTPException, Request

from clashtx.config import ConfigStore
from clashtx.config.store import _read_json, _write_json

COOKIE = 'clashtx_session'
SESSION_SECONDS = 12 * 3600
ITERATIONS = 600_000


class WebAuth:
    def __init__(self, store: ConfigStore, password: str | None = None):
        self.store = store
        self.path = store.paths.config_dir / 'web-auth.json'
        self.lock = threading.RLock()
        self.sessions: dict[str, tuple[float, str]] = {}
        self.attempts: dict[str, deque[float]] = defaultdict(deque)
        with store.transaction():
            if password is not None or not self.path.exists():
                self.set_password('7897' if password is None else password)
            self.fingerprint = self._credentials()['hash']
            self.path.chmod(0o600)

    def set_password(self, password: str) -> None:
        if not password or len(password) > 256:
            raise ValueError('Password must contain 1–256 characters.')
        salt = secrets.token_bytes(16)
        value = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, ITERATIONS)
        with self.store.transaction():
            _write_json(self.path, {'salt': salt.hex(), 'hash': value.hex(), 'iterations': ITERATIONS})

    def _credentials(self) -> dict:
        with self.store.transaction():
            credentials = _read_json(self.path)
        if not credentials.get('hash') or credentials.get('iterations') != ITERATIONS:
            raise RuntimeError('Web authentication file is invalid; reset it with ui --password.')
        return credentials

    def _refresh(self) -> dict:
        credentials = self._credentials()
        if credentials['hash'] != self.fingerprint:
            self.sessions.clear()
            self.fingerprint = credentials['hash']
        now = time.monotonic()
        self.sessions = {key: value for key, value in self.sessions.items() if value[0] > now}
        self.attempts = defaultdict(deque, {
            key: deque(value for value in values if value > now - 60)
            for key, values in self.attempts.items() if values and values[-1] > now - 60
        })
        return credentials

    def login(self, request: Request, password: str) -> tuple[str, str]:
        with self.lock:
            credentials = self._refresh()
            address = request.client.host if request.client else 'unknown'
            attempts = self.attempts[address]
            if len(attempts) >= 5:
                raise HTTPException(429, 'Too many failed logins; try again in one minute.', headers={'Retry-After': '60'})
            value = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(credentials['salt']), ITERATIONS)
            if not hmac.compare_digest(value.hex(), credentials['hash']):
                attempts.append(time.monotonic())
                raise HTTPException(401, 'Incorrect password.')
            self.attempts.pop(address, None)
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            # Store a digest so an in-memory session index is not a bearer credential.
            self.sessions[hashlib.sha256(token.encode()).hexdigest()] = (time.monotonic() + SESSION_SECONDS, csrf)
            return token, csrf

    def session(self, request: Request) -> str:
        with self.lock:
            self._refresh()
            token = request.cookies.get(COOKIE, '')
            entry = self.sessions.get(hashlib.sha256(token.encode()).hexdigest())
            if entry is None:
                raise HTTPException(401, 'Login required.')
            return entry[1]

    def logout(self, request: Request) -> None:
        with self.lock:
            self.sessions.pop(hashlib.sha256(request.cookies.get(COOKIE, '').encode()).hexdigest(), None)

    def check_csrf(self, request: Request, csrf: str) -> None:
        if not hmac.compare_digest(request.headers.get('X-CSRF-Token', ''), csrf):
            raise HTTPException(403, 'Invalid CSRF token.')
