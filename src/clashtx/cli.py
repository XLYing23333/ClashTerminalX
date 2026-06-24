from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

from clashtx import AUTHOR, __version__

try:
    from rich.console import Console
except ModuleNotFoundError:
    Console = None

COMMANDS = {
    "stop",
    "status",
    "start",
    "restart",
    "help",
    "ui",
    "mode",
    "source",
}


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    console = _console()
    if not args:
        from clashtx.tui.app import ClashTXApp

        ClashTXApp().run()
        return 0

    command = args[0]
    if command not in COMMANDS:
        _print_error(console, f"Unknown command: {command}")
        _print_help(console)
        return 2

    if command == "help":
        _print_help(console)
        return 0

    if command == "ui":
        return _run_ui(args[1:], console)

    if command == "mode":
        return _run_mode(args[1:], console)

    if command == "source":
        return _run_source(console)

    from clashtx.config import ConfigStore
    from clashtx.system import ServiceManager

    store = ConfigStore()
    service = ServiceManager(store)

    try:
        if command == "start":
            _print_success(console, service.start())
            _note_proxy_env(console)
        elif command == "stop":
            _print_success(console, service.stop())
        elif command == "restart":
            _print_success(console, service.restart())
            _note_proxy_env(console)
        elif command == "status":
            status = service.status()
            active_style = "green" if status.active else "yellow"
            console.print("[bold cyan]STATUS[/]")
            # console.print(f"Installed: {status.installed}")
            console.print(f"Active:  [{active_style}]{status.active}[/]")
            if status.text:
                console.print(status.text)
    except Exception as exc:
        _print_error(console, str(exc))
        return 1
    return 0


def _run_mode(args: list[str], console) -> int:
    if len(args) != 1 or args[0] not in {"system", "tun"}:
        _print_error(console, "Usage: clashtx mode system|tun")
        return 2

    from clashtx.controller import ClashTXController

    try:
        message = ClashTXController().set_network_mode(args[0])
    except Exception as exc:
        _print_error(console, str(exc))
        return 1
    _print_success(console, message)
    return 0


def _run_source(console) -> int:
    from clashtx.system.proxy import ProxyManager

    env_file = ProxyManager().env_file
    if not env_file.exists():
        _print_error(
            console,
            f"Proxy env not found: {env_file}. Run: clashtx mode system",
        )
        return 1
    console.print(
        "Load proxy into the current shell with:\n"
        f"  source {env_file}\n"
        "Or, if you use clashtx.sh:\n"
        "  source ./clashtx.sh source\n"
        "  source ./clashtx.sh start"
    )
    return 0


def _note_proxy_env(console) -> None:
    if os.environ.get("CLASHTX_SHELL") == "1":
        return

    from clashtx.system.proxy import ProxyManager

    env_file = ProxyManager().env_file
    if not env_file.exists():
        return
    console.print(
        "Load proxy into the current shell with:\n"
        f"  source {env_file}\n"
        "Or, if you use clashtx.sh:\n"
        "  source ./clashtx.sh start"
    )


def _run_ui(args: list[str], console) -> int:
    parser = argparse.ArgumentParser(prog="clashtx ui", add_help=True)
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=7887, help="Listen port (default: 7887)")
    options = parser.parse_args(args)

    from clashtx.web import run_ui

    _print_success(
        console,
        f"ClashTX Web UI listening on http://{options.host}:{options.port}  ·  {AUTHOR}",
    )
    try:
        run_ui(host=options.host, port=options.port)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        _print_error(console, str(exc))
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clashtx", add_help=False)
    parser.add_argument("command", nargs="?", choices=sorted(COMMANDS))
    return parser


def _console():
    if Console is not None:
        return Console()
    return PlainConsole()


class PlainConsole:
    def print(self, *objects, **kwargs) -> None:
        text = " ".join(str(item) for item in objects)
        for token in (
            "[red]",
            "[green]",
            "[yellow]",
            "[cyan]",
            "[bold red]",
            "[bold green]",
            "[bold cyan]",
            "[/]",
        ):
            text = text.replace(token, "")
        print(text)


def _print_success(console, message: str) -> None:
    console.print(f"[bold green]✅ SUCCESS[/] {message}")


def _print_error(console, message: str) -> None:
    console.print(f"[bold red]❌ ERROR[/] {message}")


def _print_help(console) -> None:
    console.print(f"ClashTX {__version__}  ·  {AUTHOR}")
    console.print("Usage: clashtx [command]\n")
    console.print("No command starts the Textual TUI.")
    console.print("Commands:")
    console.print("  start        Start the Mihomo core service (auto-loads proxy via clashtx.sh)")
    console.print("  stop         Stop the Mihomo core service")
    console.print("  restart      Restart the Mihomo core service (auto-loads proxy via clashtx.sh)")
    console.print("  status       Show service status")
    console.print("  ui           Start the Web UI (default: 0.0.0.0:7887)")
    console.print("  mode         Switch network mode: system | tun")
    console.print("  source       Show how to load proxy.env into the current shell")
    console.print("  help         Show this help")
