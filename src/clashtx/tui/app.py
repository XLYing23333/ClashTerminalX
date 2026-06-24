from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from rich.markup import escape
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Select,
    Static,
    TabbedContent,
    TabPane,
)
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from clashtx import AUTHOR
from clashtx.config import ConfigStore
from clashtx.core import CoreManager
from clashtx.mihomo import MihomoAPI
from clashtx.controller import (
    AUTO_GROUPS,
    PRIMARY_GROUPS,
    ClashTXController,
    format_test_all_message,
    is_proxy_node,
    pick_primary_node,
)
from clashtx.subscription import SubscriptionManager
from clashtx.system import ServiceManager
from clashtx.system.proxy import ProxyManager

ACTIVE_SUB_MARKER = "🟢"
GROUP_SELECT_PLACEHOLDER = ("Loading groups...", "")
try:
    SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
except ZoneInfoNotFoundError:
    SHANGHAI_TZ = timezone(timedelta(hours=8), "Asia/Shanghai")

ERROR_MARKERS = (
    "failed",
    "unable",
    "error",
    "must",
    "missing",
    "invalid",
    "not a real",
)
WARNING_MARKERS = ("select ", "not listening", "reload failed", "unavailable")
SUCCESS_MARKERS = (
    "started",
    "stopped",
    "restarted",
    "saved",
    "enabled",
    "disabled",
    "updated",
    "deleted",
    "using",
    "selected",
    "complete",
    "switched",
    "loaded",
    "refreshed",
)


def format_delay_cell(delay: int | None) -> Text:
    if delay is None:
        return Text("-", style="dim")
    label = Text(str(delay))
    if delay < 0:
        label.stylize("bold red")
    elif delay <= 150:
        label.stylize("bold green")
    elif delay <= 400:
        label.stylize("bold yellow")
    else:
        label.stylize("bold red")
    return label


def format_status_message(message: str) -> str:
    lowered = message.lower()
    safe_message = escape(message)
    if any(marker in lowered for marker in ERROR_MARKERS):
        return f"[bold red]❌ FAILED[/] {safe_message}"
    if any(marker in lowered for marker in WARNING_MARKERS):
        return f"[bold yellow]⚠ NOTICE[/] {safe_message}"
    if any(marker in lowered for marker in SUCCESS_MARKERS):
        return f"[bold green]✅ SUCCESS[/] {safe_message}"
    return f"[bold cyan] INFO[/] {safe_message}"


def format_shanghai_time(value: str | None) -> str:
    if not value:
        return "never"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(SHANGHAI_TZ).strftime("%Y-%m-%d %H:%M:%S")


class ClashTXApp(App):
    CSS_PATH = "style.tcss"
    THEME = "atom-one-dark"
    TITLE = "ClashTX"
    SUB_TITLE = f"ClashTerminalX"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("s", "start", "Start"),
        ("x", "stop", "Stop"),
    ]

    status_text = reactive("Ready")

    def __init__(self) -> None:
        super().__init__()
        self.store = ConfigStore()
        self.core = CoreManager(self.store)
        self.service = ServiceManager(self.store, self.core)
        self.subscription = SubscriptionManager(self.store)
        self.proxy = ProxyManager(self.store)
        self.api = MihomoAPI(self.store)
        self.ctl = ClashTXController(self.store)
        self.selected_subscription_name: str | None = None
        self.selected_node: tuple[str, str] | None = None
        self.node_data: dict | None = None
        self.traffic_points: list[tuple[int, int]] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="root"):
            yield Static("󰕥 ClashTX", id="brand")
            with TabbedContent(initial="dashboard"):
                with TabPane("Dashboard", id="dashboard"):
                    yield Static("", id="dashboard-status", classes="dashboard-line", markup=True)
                    yield Static("", id="dashboard-selection", classes="dashboard-line", markup=True)
                    yield Static("", id="traffic-chart", markup=True)
                    with Horizontal(classes="button-row"):
                        yield Button("Start", id="start", variant="success")
                        yield Button("Stop", id="stop", variant="error")
                        yield Button("Restart", id="restart", variant="warning")
                    yield Static("", id="core-version", classes="dashboard-line")
                with TabPane("Proxy", id="proxy"):
                    with VerticalScroll(id="proxy-scroll"):
                        yield Static("", id="network-mode-status", classes="proxy-section", markup=True)
                        with Horizontal(classes="button-row"):
                            yield Button("System Mode", id="mode-system", variant="primary")
                            yield Button("TUN Mode", id="mode-tun", variant="warning")
                        yield Static("System Proxy", classes="proxy-section-title")
                        yield Static("", id="proxy-status", classes="proxy-section", markup=True)
                        yield Input(placeholder="Proxy host", id="proxy-host")
                        yield Input(placeholder="Proxy port (Mihomo mixed-port)", id="proxy-port")
                        yield Input(placeholder="No proxy hosts", id="proxy-no-proxy")
                        with Horizontal(classes="button-row"):
                            yield Button("Apply", id="proxy-apply", variant="primary")
                            yield Button("Enable", id="proxy-enable", variant="success")
                            yield Button("Disable", id="proxy-disable", variant="error")
                            yield Button("Refresh", id="proxy-refresh", variant="warning")
                        yield Static("", id="proxy-hint", classes="proxy-hint", markup=True)
                        yield Static("TUN", classes="proxy-section-title")
                        yield Static("", id="tun-status", classes="proxy-section", markup=True)
                with TabPane("Subscriptions", id="subscriptions"):
                    yield Input(placeholder="Subscription name", id="sub-name")
                    yield Input(placeholder="Subscription URL", id="sub-url")
                    with Horizontal(classes="button-row"):
                        yield Button("Add / Replace", id="sub-save", variant="primary")
                        yield Button("Use Selected", id="sub-activate", variant="success")
                        yield Button("Update Selected", id="sub-update", variant="warning")
                        yield Button("Update All", id="sub-update-all", variant="primary")
                        yield Button("Delete Selected", id="sub-delete", variant="error")
                    yield DataTable(id="sub-table", zebra_stripes=True)
                with TabPane("Nodes", id="nodes"):
                    with Horizontal(classes="button-row"):
                        yield Select([GROUP_SELECT_PLACEHOLDER], id="group-select", allow_blank=True)
                        yield Select(
                            [("Rule", "rule"), ("Global", "global"), ("Direct", "direct")],
                            id="mode-select",
                            allow_blank=False,
                        )
                        yield Select(
                            [("Latency", "latency"), ("A-Z", "a-z"), ("Z-A", "z-a")],
                            id="sort-select",
                            allow_blank=False,
                        )
                        yield Button("Refresh", id="refresh-nodes", variant="primary")
                        yield Button("Select Node", id="select-node", variant="success")
                        yield Button("Test Selected", id="test-node", variant="warning")
                        yield Button("Test All", id="test-all-nodes", variant="primary")
                    yield Static("", id="group-summary", classes="dashboard-line", markup=True)
                    yield DataTable(id="node-table", zebra_stripes=True)
            yield Static("", id="status-bar", markup=True)
            yield Static(f"by {AUTHOR}", id="author-credit", classes="author-credit")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#node-table", DataTable).add_columns("Node", "Delay")
        sub_table = self.query_one("#sub-table", DataTable)
        sub_table.add_column("Active", width=5, key="active")
        sub_table.add_column("Name", key="name")
        sub_table.add_column("Updated", key="updated")
        sub_table.add_column("URL", key="url")
        self._load_settings()
        self.refresh_dashboard()
        self.refresh_subscriptions()
        self.refresh_nodes()
        self.refresh_proxy()
        self.set_interval(1.5, self.refresh_traffic)

    def watch_status_text(self, value: str) -> None:
        self.query_one("#status-bar", Static).update(format_status_message(value))

    def action_refresh(self) -> None:
        self.refresh_dashboard()
        self.refresh_nodes()
        self.refresh_proxy()

    def action_start(self) -> None:
        self._run_service("start")

    def action_stop(self) -> None:
        self._run_service("stop")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id in {"start", "stop", "restart"}:
            self._run_service(button_id)
        elif button_id == "sub-save":
            name = self.query_one("#sub-name", Input).value.strip()
            url = self.query_one("#sub-url", Input).value.strip()
            self.save_subscription(name, url)
        elif button_id == "sub-activate":
            self.activate_subscription(self._selected_subscription())
        elif button_id == "sub-update":
            self.update_subscription(self._selected_subscription())
        elif button_id == "sub-update-all":
            self.update_all_subscriptions()
        elif button_id == "sub-delete":
            self.delete_subscription(self._selected_subscription())
        elif button_id == "refresh-nodes":
            self.refresh_nodes()
        elif button_id == "select-node":
            self.select_selected_node()
        elif button_id == "test-node":
            self.test_selected_node()
        elif button_id == "test-all-nodes":
            self.test_all_nodes()
        elif button_id == "proxy-apply":
            self.apply_proxy_settings()
        elif button_id == "proxy-enable":
            self.enable_proxy()
        elif button_id == "proxy-disable":
            self.disable_proxy()
        elif button_id == "proxy-refresh":
            self.refresh_proxy()
        elif button_id == "mode-system":
            self.set_network_mode("system")
        elif button_id == "mode-tun":
            self.set_network_mode("tun")

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        self.action_refresh()
        if event.tab.id == "subscriptions":
            self.refresh_subscriptions()

    def on_select_changed(self, event: Select.Changed) -> None:
        config = self.store.load_config()
        if event.select.id == "group-select":
            if not isinstance(event.value, str) or not event.value:
                return
            config.active_node_group = event.value
            self.store.save_config(config)
            self.selected_node = None
            if self.node_data:
                self._render_node_table(event.value)
            return
        if event.select.id == "mode-select" and isinstance(event.value, str):
            config.proxy_mode = event.value
            self.store.save_config(config)
            self.set_mode(event.value)
        elif event.select.id == "sort-select" and isinstance(event.value, str):
            config.sort_mode = event.value
            self.store.save_config(config)
            self.refresh_nodes()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "node-table":
            values = event.data_table.get_row(event.row_key)
            if len(values) >= 1:
                group = self._active_node_group()
                if group:
                    self.selected_node = (group, str(values[0]))
                    self.status_text = f"Selected row: {group} -> {values[0]}"
        elif event.data_table.id == "sub-table":
            values = event.data_table.get_row(event.row_key)
            if len(values) >= 2:
                self._set_subscription_selection(values)

    def on_data_table_cell_selected(self, event) -> None:
        table = event.data_table
        values = table.get_row(event.cell_key.row_key)
        if table.id == "node-table" and len(values) >= 1:
            group = self._active_node_group()
            if group:
                self.selected_node = (group, str(values[0]))
                self.status_text = f"Selected row: {group} -> {values[0]}"
        elif table.id == "sub-table" and len(values) >= 2:
            self._set_subscription_selection(values)

    def refresh_dashboard(self) -> None:
        status = self.service.status()
        config = self.store.load_config()
        active_style = "green" if status.active else "yellow"
        active_text = "True" if status.active else "False"
        self.query_one("#dashboard-status", Static).update(
            f"Service active: [{active_style}]{active_text}[/] | "
            f"mode: [cyan]{config.proxy_mode}[/] | "
            f"network: [magenta]{config.network_mode}[/] | "
            f"proxy: [blue]{config.system_proxy_host}:{config.mixed_port}[/]"
        )
        node_text = "No node selected"
        if status.active:
            try:
                node_text = pick_primary_node(
                    self.api.groups(),
                    from_config=config.selected_nodes,
                    preferred_group=config.active_node_group,
                )
            except Exception:
                node_text = pick_primary_node(
                    [],
                    from_config=config.selected_nodes,
                    preferred_group=config.active_node_group,
                )
        else:
            node_text = pick_primary_node(
                [],
                from_config=config.selected_nodes,
                preferred_group=config.active_node_group,
            )
        self.query_one("#dashboard-selection", Static).update(
            f"Subscription: [magenta]{config.active_subscription or 'none'}[/] | "
            f"Node: [green]{node_text}[/]"
        )
        self.query_one("#core-version", Static).update(
            f"Core: {self.core.version() or 'not installed'}"
        )
        self.status_text = "Dashboard refreshed."

    def refresh_proxy(self) -> None:
        config = self.store.load_config()
        network = self.ctl.network_status()
        proxy_status = network["proxy"]
        tun = network["tun"]
        self.query_one("#proxy-host", Input).value = config.system_proxy_host
        self.query_one("#proxy-port", Input).value = str(config.mixed_port)
        self.query_one("#proxy-no-proxy", Input).value = config.system_proxy_no_proxy

        mode_style = "green" if network["mode"] == "tun" else "cyan"
        self.query_one("#network-mode-status", Static).update(
            f"Active mode: [{mode_style}]{network['mode']}[/]"
        )

        tun_style = "green" if tun["enabled"] else "yellow"
        device_style = "green" if tun["device_available"] else "yellow"
        caps_style = "green" if tun.get("capabilities_ready", True) else "red"
        caps_text = "Yes" if tun.get("capabilities_ready", True) else "No"
        self.query_one("#tun-status", Static).update(
            f"TUN: [{tun_style}]{'Enabled' if tun['enabled'] else 'Disabled'}[/] | "
            f"device: [{device_style}]{'Yes' if tun['device_available'] else 'No'}[/] | "
            f"caps: [{caps_style}]{caps_text}[/]\n"
            f"Tools: [cyan]{tun['tools_dir']}[/]\n"
            f"{tun['message']}"
        )

        enabled_style = "green" if proxy_status["enabled"] else "yellow"
        enabled_text = "Enabled" if proxy_status["enabled"] else "Disabled"
        listening_style = "green" if proxy_status["port_listening"] else "yellow"
        listening_text = "Yes" if proxy_status["port_listening"] else "No"
        gnome_text = proxy_status["gnome_mode"] or "unavailable"
        gnome_style = "green" if proxy_status["gnome_mode"] == "manual" else "yellow"
        allow_proxy = network["system_proxy_allowed"]

        self.query_one("#proxy-status", Static).update(
            f"Status: [{enabled_style}]{enabled_text}[/]\n"
            f"Mihomo listening: [{listening_style}]{listening_text}[/] "
            f"at [blue]{proxy_status['host']}:{proxy_status['port']}[/]\n"
            f"GNOME proxy: [{gnome_style}]{gnome_text}[/] | "
            f"env file: {'present' if proxy_status['env_exists'] else 'missing'}"
            + (
                "\n[yellow]System proxy disabled while TUN mode is active.[/]"
                if not allow_proxy
                else ""
            )
        )
        self.query_one("#proxy-enable", Button).disabled = not allow_proxy
        self.query_one("#proxy-apply", Button).disabled = not allow_proxy
        self.query_one("#proxy-hint", Static).update(
            f"Server shell: [cyan]source {proxy_status['env_file']}[/]\n"
            f"CLI: [cyan]clashtx mode system[/] or [cyan]clashtx mode tun[/]"
        )

    def refresh_subscriptions(self) -> None:
        table = self.query_one("#sub-table", DataTable)
        table.clear()
        config = self.store.load_config()
        for item in config.subscriptions:
            if item.name == config.active_subscription:
                marker = f" {ACTIVE_SUB_MARKER} "
            else:
                marker = ""
            table.add_row(
                marker,
                item.name,
                format_shanghai_time(item.updated_at),
                item.url,
                key=item.name,
            )

    def refresh_nodes(self) -> None:
        self.load_nodes()

    @work(thread=True)
    def load_nodes(self) -> None:
        try:
            data = self.ctl.list_nodes()
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Unable to load nodes: {exc}")
            return
        self.call_from_thread(self._apply_node_data, data)

    def _apply_node_data(self, data: dict) -> None:
        self.node_data = data
        options: list[tuple[str, str]] = []
        for group in data["groups"]:
            if not group["nodes"]:
                continue
            marker = " *" if group.get("now") else ""
            auto = " [auto]" if not group["selectable"] else ""
            label = f"{group['name']}{marker} [{group['type']}]{auto}"
            options.append((label, group["name"]))
        active_group = data.get("active_group")
        if active_group:
            self._set_select_options("#group-select", options, active_group)
            self._render_node_table(active_group)
        else:
            group_select = self.query_one("#group-select", Select)
            group_select.set_options([("No groups", "")])
            group_select.value = Select.NULL
            self.query_one("#group-summary", Static).update("No proxy groups loaded.")
            self.query_one("#node-table", DataTable).clear()
        self.query_one("#mode-select", Select).value = data["mode"]
        self.query_one("#sort-select", Select).value = data["sort_mode"]
        group_count = len([group for group in data["groups"] if group["nodes"]])
        node_count = sum(len(group["nodes"]) for group in data["groups"])
        self.status_text = f"Loaded {group_count} groups, {node_count} nodes."

    def _render_node_table(self, group_name: str) -> None:
        if not self.node_data:
            return
        group = next(
            (item for item in self.node_data["groups"] if item["name"] == group_name),
            None,
        )
        if group is None:
            return
        table = self.query_one("#node-table", DataTable)
        table.clear()
        for entry in group["nodes"]:
            table.add_row(entry["node"], format_delay_cell(entry["delay"]))
        now = group.get("now") or "none"
        selectable = "[green]manual[/]" if group["selectable"] else "[yellow]auto[/]"
        self.query_one("#group-summary", Static).update(
            f"Group: [cyan]{group_name}[/] | type: {group['type']} | "
            f"mode: {selectable} | active: [green]{now}[/]"
        )

    def _active_node_group(self) -> str | None:
        value = self.query_one("#group-select", Select).value
        return str(value) if isinstance(value, str) and value else None

    def _set_select_options(self, selector: str, options: list[tuple[str, str]], value: str) -> None:
        select = self.query_one(selector, Select)
        if not options:
            select.set_options([("No groups", "")])
            select.value = Select.NULL
            return
        select.set_options(options)
        select.value = value

    @work(thread=True)
    def set_mode(self, mode: str) -> None:
        try:
            self.api.set_mode(mode)
            self.call_from_thread(self._set_status, f"Mode switched to {mode}.")
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Mode saved locally, API failed: {exc}")

    @work(thread=True)
    def select_node(self, group: str, node: str) -> None:
        try:
            updated = self.ctl.select_node(group, node)
            if len(updated) > 1:
                message = f"Selected {node} for {group} (synced: {', '.join(updated)})"
            else:
                message = f"Selected {node} for {group}."
            self.call_from_thread(self._set_status, message)
            self.call_from_thread(self.refresh_dashboard)
            self.call_from_thread(self.refresh_nodes)
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Unable to select node: {exc}")

    def select_selected_node(self) -> None:
        try:
            group, node = self._selected_node(require_row=True)
        except ValueError as exc:
            self.status_text = str(exc)
            return
        self.select_node(group, node)

    def test_selected_node(self) -> None:
        try:
            group, node = self._selected_node()
        except ValueError as exc:
            self.status_text = str(exc)
            return
        self.test_node(group, node)

    @work(thread=True)
    def test_node(self, group: str, node: str) -> None:
        try:
            delay = self.api.delay(node)
            self.call_from_thread(self.refresh_nodes)
            self.call_from_thread(self._set_status, f"{node} delay: {delay} ms.")
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Delay test failed for {node}: {exc}")

    @work(thread=True)
    def test_all_nodes(self) -> None:
        def on_progress(done: int, total: int, node: str | None) -> None:
            if done == 0:
                message = f"Starting concurrent latency test for {total} nodes..."
            else:
                current = node or "..."
                message = f"Testing nodes {done}/{total} — {current}"
            self.call_from_thread(self._set_status, message)

        try:
            result = self.ctl.test_all_nodes(progress=on_progress)
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Unable to test nodes: {exc}")
            return
        self.call_from_thread(self.refresh_dashboard)
        self.call_from_thread(self.refresh_nodes)
        self.call_from_thread(self._set_status, format_test_all_message(result))

    @work(thread=True)
    def save_subscription(self, name: str, url: str) -> None:
        if not name or not url:
            self.call_from_thread(self._set_status, "Subscription name and URL are required.")
            return
        try:
            subscription = self.subscription.add_or_update(name, url)
            self.selected_subscription_name = subscription.name
            self.call_from_thread(self.refresh_subscriptions)
            self.call_from_thread(self.refresh_dashboard)
            self.call_from_thread(self.refresh_nodes)
            self.call_from_thread(
                self._set_status,
                f"Updated subscription {subscription.name}. {self._reload_config_message()}",
            )
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Subscription update failed: {exc}")

    @work(thread=True)
    def activate_subscription(self, name: str | None) -> None:
        if not name:
            self.call_from_thread(self._set_status, "Select a subscription first.")
            return
        try:
            subscription = self.subscription.activate(name)
            self.call_from_thread(self.refresh_subscriptions)
            self.call_from_thread(self.refresh_dashboard)
            self.call_from_thread(self.refresh_nodes)
            self.call_from_thread(
                self._set_status,
                f"Using subscription {subscription.name}. {self._reload_config_message()}",
            )
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Unable to use subscription: {exc}")

    @work(thread=True)
    def update_subscription(self, name: str | None) -> None:
        if not name:
            self.call_from_thread(self._set_status, "Select a subscription first.")
            return
        try:
            subscription = self.subscription.update(name)
            self.call_from_thread(self.refresh_subscriptions)
            self.call_from_thread(self.refresh_dashboard)
            self.call_from_thread(self.refresh_nodes)
            self.call_from_thread(
                self._set_status,
                f"Updated subscription {subscription.name}. {self._reload_config_message()}",
            )
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Subscription update failed: {exc}")

    @work(thread=True)
    def update_all_subscriptions(self) -> None:
        def on_progress(done: int, total: int, name: str, error: str | None) -> None:
            if error is None:
                message = f"Updating subscription {done}/{total}: {name}"
            elif error:
                message = f"Subscription {done}/{total} failed: {name} ({error})"
            else:
                message = f"Subscription {done}/{total} updated: {name}"
            self.call_from_thread(self._set_status, message)

        try:
            result = self.ctl.refresh_all_subscriptions(progress=on_progress)
            self.call_from_thread(self.refresh_subscriptions)
            self.call_from_thread(self.refresh_dashboard)
            self.call_from_thread(self.refresh_nodes)
            message = (
                f"Subscription update complete: {result['success_count']} succeeded, "
                f"{result['failure_count']} failed."
            )
            if result["failed"]:
                failures = "; ".join(
                    f"{item['name']} ({item['error']})" for item in result["failed"]
                )
                message += f" Failed: {failures}"
            self.call_from_thread(self._set_status, message)
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Subscription update failed: {exc}")

    @work(thread=True)
    def delete_subscription(self, name: str | None) -> None:
        if not name:
            self.call_from_thread(self._set_status, "Select a subscription first.")
            return
        try:
            self.subscription.delete(name)
            if self.selected_subscription_name == name:
                self.selected_subscription_name = None
            self.call_from_thread(self.refresh_subscriptions)
            self.call_from_thread(self.refresh_dashboard)
            self.call_from_thread(self.refresh_nodes)
            self.call_from_thread(
                self._set_status,
                f"Deleted subscription {name}. {self._reload_config_message()}",
            )
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Unable to delete subscription: {exc}")

    def apply_proxy_settings(self) -> None:
        host = self.query_one("#proxy-host", Input).value.strip()
        port_text = self.query_one("#proxy-port", Input).value.strip()
        no_proxy = self.query_one("#proxy-no-proxy", Input).value.strip()
        try:
            port = int(port_text)
        except ValueError:
            self.status_text = "Proxy port must be a number."
            return
        self._apply_proxy_settings(host, port, no_proxy)

    @work(thread=True)
    def set_network_mode(self, mode: str) -> None:
        try:
            message = self.ctl.set_network_mode(mode)
            self.call_from_thread(self.refresh_proxy)
            self.call_from_thread(self.refresh_dashboard)
            self.call_from_thread(self._set_status, message)
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Network mode switch failed: {exc}")

    @work(thread=True)
    def _apply_proxy_settings(self, host: str, port: int, no_proxy: str) -> None:
        try:
            self.proxy.apply_settings(host, port, no_proxy)
            self.subscription.generate_runtime_config()
            try:
                if self.service.status().active:
                    self.api.reload_config()
            except Exception:
                pass
            self.call_from_thread(self.refresh_proxy)
            self.call_from_thread(self.refresh_dashboard)
            self.call_from_thread(self._set_status, "Proxy settings saved.")
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Unable to save proxy settings: {exc}")

    @work(thread=True)
    def enable_proxy(self) -> None:
        try:
            path = self.proxy.enable()
            hint = f"System proxy enabled. Source: source {path}"
            if not self.proxy.port_open():
                hint += " | Mihomo port is not listening yet"
            self.call_from_thread(self.refresh_proxy)
            self.call_from_thread(self._set_status, hint)
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Enable proxy failed: {exc}")

    @work(thread=True)
    def disable_proxy(self) -> None:
        try:
            self.proxy.disable()
            self.call_from_thread(self.refresh_proxy)
            self.call_from_thread(self._set_status, "System proxy disabled.")
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Disable proxy failed: {exc}")

    @work(thread=True)
    def _run_service(self, action: str) -> None:
        try:
            message = getattr(self.service, action)()
            self.call_from_thread(self._set_status, message)
            self.call_from_thread(self.refresh_dashboard)
            self.call_from_thread(self.refresh_nodes)
            self.call_from_thread(self.refresh_proxy)
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Service {action} failed: {exc}")

    def _load_settings(self) -> None:
        config = self.store.load_config()
        self.query_one("#mode-select", Select).value = config.proxy_mode
        self.query_one("#sort-select", Select).value = config.sort_mode

    def _set_status(self, message: str) -> None:
        self.status_text = message

    def _selected_subscription(self) -> str | None:
        if self.selected_subscription_name:
            return self.selected_subscription_name
        config = self.store.load_config()
        return config.active_subscription

    def _selected_node(self, *, require_row: bool = False) -> tuple[str, str]:
        if self.selected_node:
            group, node = self.selected_node
            if group in AUTO_GROUPS:
                raise ValueError(f"{group} is automatic; select a node under GLOBAL or selector group.")
            if not is_proxy_node(node):
                raise ValueError(f"{node} is not a real proxy node.")
            return self.selected_node
        if require_row:
            raise ValueError("Select a node row first.")
        config = self.store.load_config()
        if config.selected_nodes:
            for preferred in PRIMARY_GROUPS:
                if preferred in config.selected_nodes:
                    group, node = preferred, config.selected_nodes[preferred]
                    if is_proxy_node(node) and group not in AUTO_GROUPS:
                        return group, node
            for group, node in config.selected_nodes.items():
                if group not in AUTO_GROUPS and is_proxy_node(node):
                    return group, node
        raise ValueError("Select a node row first.")

    def _set_subscription_selection(self, values) -> None:
        self.selected_subscription_name = str(values[1])
        self.query_one("#sub-name", Input).value = str(values[1])
        self.query_one("#sub-url", Input).value = str(values[3]) if len(values) > 3 else ""
        self.status_text = f"Selected subscription: {self.selected_subscription_name}"

    def _reload_config_message(self) -> str:
        try:
            self.api.reload_config()
            return "Mihomo config reloaded."
        except Exception as exc:
            return f"Config saved, reload failed: {exc}"

    def _set_select_value(self, selector: str, value: str) -> None:
        if selector == "#group-select" and self.node_data:
            self._set_select_options(selector, self._group_select_options(), value)
            self._render_node_table(value)
            return
        self.query_one(selector, Select).value = value

    def _group_select_options(self) -> list[tuple[str, str]]:
        if not self.node_data:
            return []
        options: list[tuple[str, str]] = []
        for group in self.node_data["groups"]:
            if not group["nodes"]:
                continue
            marker = " *" if group.get("now") else ""
            auto = " [auto]" if not group["selectable"] else ""
            label = f"{group['name']}{marker} [{group['type']}]{auto}"
            options.append((label, group["name"]))
        return options

    def refresh_traffic(self) -> None:
        self.load_traffic()

    @work(thread=True)
    def load_traffic(self) -> None:
        try:
            up, down = self.api.traffic_sample()
        except Exception:
            return
        self.traffic_points.append((up, down))
        self.traffic_points = self.traffic_points[-32:]
        self.call_from_thread(self._render_traffic)

    def _render_traffic(self) -> None:
        up_values = [point[0] for point in self.traffic_points]
        down_values = [point[1] for point in self.traffic_points]
        up_rate = self._format_rate(up_values[-1] if up_values else 0)
        down_rate = self._format_rate(down_values[-1] if down_values else 0)
        traffic_chart = self.query_one("#traffic-chart", Static)
        rate_width = 12
        label_width = 7
        gap_width = 2
        chart_width = max(8, traffic_chart.size.width - label_width - gap_width - rate_width)
        traffic_chart.update(
            f"[bold][green]▲ UP[/]   {self._sparkline(up_values, chart_width)}  "
            f"[green]{(up_rate + '/s').rjust(rate_width)}[/][/]\n"
            f"[bold][blue]▼ DOWN[/] {self._sparkline(down_values, chart_width)}  "
            f"[blue]{(down_rate + '/s').rjust(rate_width)}[/][/]"
        )

    def _sparkline(self, values: list[int], width: int = 32) -> str:
        visible_values = values[-width:]
        values = [0] * max(0, width - len(visible_values)) + visible_values
        blocks = "▁▂▃▄▅▆▇█"
        highest = max(values) or 1
        return "".join(blocks[min(len(blocks) - 1, int(value / highest * (len(blocks) - 1)))] for value in values)

    def _format_rate(self, value: int) -> str:
        if value >= 1024 * 1024:
            return f"{value / 1024 / 1024:.2f} MB"
        if value >= 1024:
            return f"{value / 1024:.1f} KB"
        return f"{value} B"
