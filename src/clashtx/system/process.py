from __future__ import annotations

import ipaddress
import os
import socket
from pathlib import Path


def process_identity(pid: int) -> dict | None:
    if pid <= 1:
        return None
    proc = Path('/proc') / str(pid)
    try:
        stat = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
        if stat[0] == 'Z':
            return None
        return {'pid': pid, 'start_time': stat[19], 'exe': str((proc / 'exe').resolve(strict=True)),
                'uid': proc.stat().st_uid,
                'args': [item.decode() for item in (proc / 'cmdline').read_bytes().split(b'\0') if item]}
    except (OSError, ValueError, UnicodeError, IndexError):
        return None


def process_exists(pid: int) -> bool:
    return isinstance(pid, int) and pid > 1 and (Path('/proc') / str(pid)).exists()


def matches(identity: dict | None) -> bool:
    return bool(identity and process_identity(identity.get('pid', 0)) == identity)


def is_core(identity: dict | None, binary: Path, config: Path, controller: str | None = None) -> bool:
    if not identity or identity['uid'] != os.getuid() or identity['exe'] != str(binary.resolve()):
        return False
    args = identity['args']
    def argument(flag):
        try:
            index = args.index(flag)
            return args[index + 1] if args.count(flag) == 1 else None
        except (ValueError, IndexError):
            return None
    try:
        return (Path(argument('-f') or '').resolve() == config.resolve()
                and Path(argument('-d') or '').resolve() == config.parent.resolve()
                and (controller is None or argument('-ext-ctl') == controller))
    except (OSError, ValueError):
        return False


def controller_address(value: str) -> tuple[str, int]:
    host, separator, port = value.rpartition(':')
    host = host.strip('[]')
    if not separator or not host or not port.isdigit() or not 1 <= int(port) <= 65535:
        raise RuntimeError('Invalid Mihomo controller address.')
    if host == 'localhost':
        host = '127.0.0.1'
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise RuntimeError('Mihomo controller must use a local IP address or localhost.') from exc
    if not address.is_loopback and not address.is_unspecified:
        raise RuntimeError('Only a local Mihomo controller can be managed safely.')
    if address.is_unspecified:
        host = '::1' if address.version == 6 else '127.0.0.1'
    return host, int(port)


def owns_listener(pid: int, value: str) -> bool:
    host, port = controller_address(value)
    try:
        inodes = set()
        for fd in (Path('/proc') / str(pid) / 'fd').iterdir():
            try:
                target = fd.readlink().as_posix()
                if target.startswith('socket:['):
                    inodes.add(target[8:-1])
            except OSError:
                continue
        for name, family in [('tcp', socket.AF_INET), ('tcp6', socket.AF_INET6)]:
            for line in (Path('/proc/net') / name).read_text().splitlines()[1:]:
                parts = line.split()
                address, raw_port = parts[1].split(':')
                if parts[3] != '0A' or int(raw_port, 16) != port or parts[9] not in inodes:
                    continue
                raw = bytes.fromhex(address)
                raw = b''.join(raw[index:index + 4][::-1] for index in range(0, len(raw), 4))
                bound = ipaddress.ip_address(socket.inet_ntop(family, raw))
                target = ipaddress.ip_address(host)
                if bound == target or (bound.is_unspecified and bound.version == target.version):
                    return True
    except (OSError, ValueError, IndexError):
        return False
    return False
