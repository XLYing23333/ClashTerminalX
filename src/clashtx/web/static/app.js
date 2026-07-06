const state = {
  tab: "dashboard",
  lang: localStorage.getItem("clashtx.lang") || "en",
  theme: localStorage.getItem("clashtx.theme") || "dark",
  selectedSub: null,
  selectedNode: null,
  activeNodeGroup: null,
  nodeData: null,
  upHistory: [],
  downHistory: [],
  trafficTimer: null,
};

const i18n = {
  en: {
    "nav.dashboard": "Dashboard",
    "nav.proxy": "Proxy",
    "nav.subscriptions": "Subscriptions",
    "nav.nodes": "Nodes",
    "footer": "Cursor & XLY23333 · Web UI",
    "title.dashboard": "Dashboard",
    "title.proxy": "System Proxy",
    "title.subscriptions": "Subscriptions",
    "title.nodes": "Nodes",
    "action.refresh": "Refresh",
    "action.start": "Start",
    "action.stop": "Stop",
    "action.restart": "Restart",
    "action.apply": "Apply",
    "action.enable": "Enable",
    "action.disable": "Disable",
    "dashboard.service": "Service",
    "dashboard.selection": "Selection",
    "dashboard.running": "Running",
    "dashboard.stopped": "Stopped",
    "dashboard.mode": "mode",
    "dashboard.network": "network",
    "dashboard.proxy": "proxy",
    "dashboard.subscription": "Subscription",
    "dashboard.node": "Node",
    "dashboard.core": "Core",
    "common.none": "none",
    "common.notInstalled": "not installed",
    "common.yes": "Yes",
    "common.no": "No",
    "common.enabled": "Enabled",
    "common.disabled": "Disabled",
    "common.unavailable": "unavailable",
    "common.present": "present",
    "common.missing": "missing",
    "common.manual": "manual",
    "common.auto": "auto",
    "proxy.activeMode": "Active mode",
    "proxy.systemMode": "System Mode",
    "proxy.tunMode": "TUN Mode",
    "proxy.systemProxy": "System Proxy",
    "proxy.host": "Host",
    "proxy.port": "Port",
    "proxy.noProxy": "No Proxy",
    "proxy.tun": "TUN",
    "proxy.device": "device",
    "proxy.caps": "caps",
    "proxy.tools": "Tools",
    "proxy.status": "Status",
    "proxy.mihomoListening": "Mihomo listening",
    "proxy.gnomeProxy": "GNOME proxy",
    "proxy.envFile": "env file",
    "proxy.disabledInTun": "System proxy disabled while TUN mode is active.",
    "proxy.serverShell": "Server shell",
    "proxy.cli": "CLI",
    "subscriptions.name": "Name",
    "subscriptions.url": "URL",
    "subscriptions.namePlaceholder": "Subscription name",
    "subscriptions.addReplace": "Add / Replace",
    "subscriptions.useSelected": "Use Selected",
    "subscriptions.updateSelected": "Update Selected",
    "subscriptions.updateAll": "Update All",
    "subscriptions.deleteSelected": "Delete Selected",
    "subscriptions.active": "Active",
    "subscriptions.updated": "Updated",
    "nodes.modeRule": "Rule",
    "nodes.modeGlobal": "Global",
    "nodes.modeDirect": "Direct",
    "nodes.sortLatency": "Latency",
    "nodes.selectNode": "Select Node",
    "nodes.testSelected": "Test Selected",
    "nodes.testAll": "Test All",
    "nodes.proxyGroups": "Proxy Groups",
    "nodes.node": "Node",
    "nodes.delay": "Delay",
    "nodes.nodes": "nodes",
    "nodes.noGroups": "No proxy groups loaded.",
    "nodes.selectGroup": "Select a proxy group.",
    "nodes.group": "Group",
    "nodes.type": "type",
    "nodes.active": "active",
    "toast.refreshed": "Refreshed.",
    "toast.networkRefreshed": "Network settings refreshed.",
    "toast.nodesRefreshed": "Nodes refreshed.",
    "toast.nameUrlRequired": "Name and URL are required.",
    "toast.selectSubscription": "Select a subscription first.",
    "toast.selectNode": "Select a node row first.",
    "toast.delay": "{node} delay: {delay} ms",
    "toast.service.start": "Service started.",
    "toast.service.stop": "Service stopped.",
    "toast.service.restart": "Service restarted.",
    "toast.proxyApplied": "Proxy settings saved.",
    "toast.proxyEnabled": "System proxy enabled.",
    "toast.proxyDisabled": "System proxy disabled.",
    "toast.networkMode": "Network mode switched to {mode}.",
    "toast.subscriptionSaved": "Saved subscription {name}.",
    "toast.subscriptionActivated": "Activated subscription {name}.",
    "toast.subscriptionUpdated": "Updated subscription {name}.",
    "toast.subscriptionUpdateAll": "Updated all subscriptions: {success} succeeded, {failed} failed.",
    "toast.subscriptionDeleted": "Deleted subscription {name}.",
    "toast.proxyMode": "Proxy mode switched to {mode}.",
    "toast.nodeSelected": "Node selected.",
    "test.start": "Starting concurrent latency test...",
    "test.running": "Testing nodes {done}/{total} — {current}",
    "test.complete": "Latency test complete: {tested}/{total} succeeded, {failed} failed. Fastest: {fastest}{delay}",
    "lang.toggle": "简中",
    "lang.aria": "Switch language",
    "theme.toLight": "Switch to light mode",
    "theme.toDark": "Switch to dark mode",
    "toast.successTitle": "✅ SUCCESS",
    "toast.errorTitle": "❌ ERROR",
    "toast.infoTitle": "ℹ INFO",
    "subscriptions.updateProgress": "Updating {done}/{total}: {name}",
    "subscriptions.updateOk": "OK {done}/{total}: {name}",
    "subscriptions.updateFailed": "FAILED {done}/{total}: {name} ({error})",
    "subscriptions.updateEmpty": "No subscriptions to update.",
  },
  zh: {
    "nav.dashboard": "仪表盘",
    "nav.proxy": "代理",
    "nav.subscriptions": "订阅",
    "nav.nodes": "节点",
    "footer": "Cursor & XLY23333 · Web 界面",
    "title.dashboard": "仪表盘",
    "title.proxy": "系统代理",
    "title.subscriptions": "订阅",
    "title.nodes": "节点",
    "action.refresh": "刷新",
    "action.start": "启动",
    "action.stop": "停止",
    "action.restart": "重启",
    "action.apply": "应用",
    "action.enable": "启用",
    "action.disable": "禁用",
    "dashboard.service": "服务",
    "dashboard.selection": "选择",
    "dashboard.running": "运行中",
    "dashboard.stopped": "已停止",
    "dashboard.mode": "模式",
    "dashboard.network": "网络",
    "dashboard.proxy": "代理",
    "dashboard.subscription": "订阅",
    "dashboard.node": "节点",
    "dashboard.core": "核心",
    "common.none": "无",
    "common.notInstalled": "未安装",
    "common.yes": "是",
    "common.no": "否",
    "common.enabled": "已启用",
    "common.disabled": "已禁用",
    "common.unavailable": "不可用",
    "common.present": "存在",
    "common.missing": "缺失",
    "common.manual": "手动",
    "common.auto": "自动",
    "proxy.activeMode": "当前模式",
    "proxy.systemMode": "System 模式",
    "proxy.tunMode": "TUN 模式",
    "proxy.systemProxy": "系统代理",
    "proxy.host": "主机",
    "proxy.port": "端口",
    "proxy.noProxy": "不代理",
    "proxy.tun": "TUN",
    "proxy.device": "设备",
    "proxy.caps": "权限",
    "proxy.tools": "工具",
    "proxy.status": "状态",
    "proxy.mihomoListening": "Mihomo 监听",
    "proxy.gnomeProxy": "GNOME 代理",
    "proxy.envFile": "环境文件",
    "proxy.disabledInTun": "TUN 模式启用时系统代理不可用。",
    "proxy.serverShell": "服务器 Shell",
    "proxy.cli": "命令行",
    "subscriptions.name": "名称",
    "subscriptions.url": "URL",
    "subscriptions.namePlaceholder": "订阅名称",
    "subscriptions.addReplace": "添加 / 替换",
    "subscriptions.useSelected": "使用选中",
    "subscriptions.updateSelected": "更新选中",
    "subscriptions.updateAll": "更新全部",
    "subscriptions.deleteSelected": "删除选中",
    "subscriptions.active": "启用",
    "subscriptions.updated": "更新时间",
    "nodes.modeRule": "规则",
    "nodes.modeGlobal": "全局",
    "nodes.modeDirect": "直连",
    "nodes.sortLatency": "延迟",
    "nodes.selectNode": "选择节点",
    "nodes.testSelected": "测试选中",
    "nodes.testAll": "测试全部",
    "nodes.proxyGroups": "代理组",
    "nodes.node": "节点",
    "nodes.delay": "延迟",
    "nodes.nodes": "个节点",
    "nodes.noGroups": "未加载代理组。",
    "nodes.selectGroup": "请选择代理组。",
    "nodes.group": "代理组",
    "nodes.type": "类型",
    "nodes.active": "当前",
    "toast.refreshed": "已刷新。",
    "toast.networkRefreshed": "网络设置已刷新。",
    "toast.nodesRefreshed": "节点已刷新。",
    "toast.nameUrlRequired": "名称和 URL 不能为空。",
    "toast.selectSubscription": "请先选择订阅。",
    "toast.selectNode": "请先选择节点行。",
    "toast.delay": "{node} 延迟：{delay} ms",
    "toast.service.start": "服务已启动。",
    "toast.service.stop": "服务已停止。",
    "toast.service.restart": "服务已重启。",
    "toast.proxyApplied": "代理设置已保存。",
    "toast.proxyEnabled": "系统代理已启用。",
    "toast.proxyDisabled": "系统代理已禁用。",
    "toast.networkMode": "网络模式已切换到 {mode}。",
    "toast.subscriptionSaved": "订阅 {name} 已保存。",
    "toast.subscriptionActivated": "订阅 {name} 已启用。",
    "toast.subscriptionUpdated": "订阅 {name} 已更新。",
    "toast.subscriptionUpdateAll": "全部订阅更新完成：成功 {success}，失败 {failed}。",
    "toast.subscriptionDeleted": "订阅 {name} 已删除。",
    "toast.proxyMode": "代理模式已切换到 {mode}。",
    "toast.nodeSelected": "节点已选择。",
    "test.start": "正在启动并发延迟测试...",
    "test.running": "正在测试节点 {done}/{total} — {current}",
    "test.complete": "延迟测试完成：成功 {tested}/{total}，失败 {failed}。最快：{fastest}{delay}",
    "lang.toggle": "EN",
    "lang.aria": "切换语言",
    "theme.toLight": "切换到浅色模式",
    "theme.toDark": "切换到深色模式",
    "toast.successTitle": "✅ 成功",
    "toast.errorTitle": "❌ 失败",
    "toast.infoTitle": "ℹ 提示",
    "subscriptions.updateProgress": "正在更新 {done}/{total}：{name}",
    "subscriptions.updateOk": "成功 {done}/{total}：{name}",
    "subscriptions.updateFailed": "失败 {done}/{total}：{name}（{error}）",
    "subscriptions.updateEmpty": "没有可更新的订阅。",
  },
};

const icons = {
  sun: `
    <svg class="bi" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M8 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8M8 0a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 0m0 13a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 13m8-5a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2A.5.5 0 0 1 16 8M3 8a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2A.5.5 0 0 1 3 8m10.657-5.657a.5.5 0 0 1 0 .707l-1.414 1.415a.5.5 0 1 1-.707-.708l1.414-1.414a.5.5 0 0 1 .707 0m-9.193 9.193a.5.5 0 0 1 0 .707L3.05 13.657a.5.5 0 0 1-.707-.707l1.414-1.414a.5.5 0 0 1 .707 0m9.193 2.121a.5.5 0 0 1-.707 0l-1.414-1.414a.5.5 0 0 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .707M4.464 4.465a.5.5 0 0 1-.707 0L2.343 3.05a.5.5 0 1 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .708"/>
    </svg>
  `,
  moon: `
    <svg class="bi" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M6 .278a.77.77 0 0 1 .858.892 7.2 7.2 0 0 0-.102 1.12c0 3.865 3.138 7.004 7.004 7.004.378 0 .751-.03 1.12-.102a.77.77 0 0 1 .891.858 8 8 0 1 1-9.67-9.772z"/>
    </svg>
  `,
};

function t(key, vars = {}) {
  const value = i18n[state.lang]?.[key] || i18n.en[key] || key;
  return value.replace(/\{(\w+)\}/g, (_, name) => vars[name] ?? "");
}

function applyTranslations() {
  document.documentElement.lang = state.lang === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  const langButton = document.getElementById("lang-toggle");
  langButton.title = t("lang.aria");
  langButton.setAttribute("aria-label", t("lang.aria"));
  const themeButton = document.getElementById("theme-toggle");
  themeButton.title = t(state.theme === "dark" ? "theme.toLight" : "theme.toDark");
  themeButton.setAttribute("aria-label", themeButton.title);
  document.getElementById("refresh-btn").title = t("action.refresh");
  document.getElementById("refresh-btn").setAttribute("aria-label", t("action.refresh"));
  document.getElementById("page-title").textContent = t(`title.${state.tab}`);
}

function applyTheme() {
  document.documentElement.dataset.theme = state.theme;
  const themeButton = document.getElementById("theme-toggle");
  if (themeButton) {
    themeButton.innerHTML = state.theme === "dark" ? icons.sun : icons.moon;
    themeButton.title = t(state.theme === "dark" ? "theme.toLight" : "theme.toDark");
    themeButton.setAttribute("aria-label", themeButton.title);
  }
}

function setTheme(theme) {
  state.theme = theme;
  localStorage.setItem("clashtx.theme", theme);
  applyTheme();
}

function setLanguage(lang) {
  state.lang = lang;
  localStorage.setItem("clashtx.lang", lang);
  applyTranslations();
  refreshTab().catch((err) => toast(err.message, true));
}

function yesNo(value) {
  return value ? t("common.yes") : t("common.no");
}

function enabledDisabled(value) {
  return value ? t("common.enabled") : t("common.disabled");
}

function noneText(value) {
  return value || t("common.none");
}

function formatShanghaiTime(value) {
  if (!value) return t("common.none");
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || response.statusText || "Request failed");
  }
  return data;
}

function toast(message, variant = "success") {
  const type = variant === true ? "error" : variant === false ? "success" : variant;
  const titleKey = type === "error" ? "toast.errorTitle" : type === "info" ? "toast.infoTitle" : "toast.successTitle";
  const el = document.getElementById("toast");
  el.innerHTML = `
    <div class="toast-title">${escapeHtml(t(titleKey))}</div>
    <div class="toast-message">${escapeHtml(message)}</div>
  `;
  el.classList.toggle("error", type === "error");
  el.classList.toggle("success", type === "success");
  el.classList.toggle("info", type === "info");
  el.classList.remove("hidden");
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.add("hidden"), type === "error" ? 6000 : 3500);
}

function formatRate(value) {
  if (value >= 1024 * 1024) return `${(value / 1024 / 1024).toFixed(2)} MB`;
  if (value >= 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${value} B`;
}

function renderSparkline(containerId, values, cssClass) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  container.classList.remove("up", "down");
  container.classList.add(cssClass);
  const max = Math.max(...values, 1);
  const windowSize = 32;
  const visibleValues = values.slice(-windowSize);
  const bars = [
    ...Array(Math.max(0, windowSize - visibleValues.length)).fill(0),
    ...visibleValues,
  ];
  bars.forEach((value) => {
    const bar = document.createElement("span");
    const height = value > 0 ? Math.max(8, Math.round((value / max) * 100)) : 0;
    bar.style.height = `${height}%`;
    if (value > 0) bar.classList.add("active");
    container.appendChild(bar);
  });
}

async function loadDashboard() {
  const data = await api("/api/dashboard");
  const badge = document.getElementById("dash-active");
  badge.textContent = data.active ? t("dashboard.running") : t("dashboard.stopped");
  badge.className = `badge ${data.active ? "on" : "off"}`;
  document.getElementById("dash-mode").textContent = `${t("dashboard.mode")}: ${data.mode}`;
  document.getElementById("dash-proxy").textContent =
    `${t("dashboard.network")}: ${data.network_mode} | ${t("dashboard.proxy")}: ${data.proxy_host}:${data.proxy_port}`;
  document.getElementById("dash-sub").textContent =
    `${t("dashboard.subscription")}: ${data.subscription || t("common.none")}`;
  document.getElementById("dash-node").textContent = `${t("dashboard.node")}: ${data.node}`;
  document.getElementById("dash-core").textContent =
    `${t("dashboard.core")}: ${data.core_version || t("common.notInstalled")}`;
}

async function loadTraffic() {
  try {
    const data = await api("/api/traffic");
    state.upHistory.push(data.up);
    state.downHistory.push(data.down);
    state.upHistory = state.upHistory.slice(-32);
    state.downHistory = state.downHistory.slice(-32);
    renderSparkline("spark-up", state.upHistory, "up");
    renderSparkline("spark-down", state.downHistory, "down");
    document.getElementById("rate-up").textContent =
      `${formatRate(data.up)}/s`;
    document.getElementById("rate-down").textContent =
      `${formatRate(data.down)}/s`;
  } catch (_) {
    /* core may be stopped */
  }
}

async function loadProxy() {
  const data = await api("/api/network");
  const proxy = data.proxy;
  const tun = data.tun;
  document.getElementById("proxy-host").value = proxy.host;
  document.getElementById("proxy-port").value = proxy.port;
  document.getElementById("proxy-no-proxy").value = proxy.no_proxy;

  document.getElementById("network-mode-status").innerHTML =
    `${t("proxy.activeMode")}: <span class="${data.mode === "tun" ? "ok" : "warn"}">${data.mode}</span>`;

  document.getElementById("tun-status-lines").innerHTML = `
    <div>TUN: <span class="${tun.enabled ? "ok" : "warn"}">${enabledDisabled(tun.enabled)}</span> | ${t("proxy.device")}: <span class="${tun.device_available ? "ok" : "warn"}">${yesNo(tun.device_available)}</span> | ${t("proxy.caps")}: <span class="${tun.capabilities_ready ? "ok" : "bad"}">${yesNo(tun.capabilities_ready)}</span></div>
    <div>${t("proxy.tools")}: <code>${escapeHtml(tun.tools_dir)}</code></div>
    <div>${escapeHtml(tun.message)}</div>
  `;

  const enabledClass = proxy.enabled ? "ok" : "warn";
  const listeningClass = proxy.port_listening ? "ok" : "warn";
  const gnomeClass = proxy.gnome_mode === "manual" ? "ok" : "warn";
  document.getElementById("proxy-status-lines").innerHTML = `
    <div>${t("proxy.status")}: <span class="${enabledClass}">${enabledDisabled(proxy.enabled)}</span></div>
    <div>${t("proxy.mihomoListening")}: <span class="${listeningClass}">${yesNo(proxy.port_listening)}</span> at ${proxy.host}:${proxy.port}</div>
    <div>${t("proxy.gnomeProxy")}: <span class="${gnomeClass}">${proxy.gnome_mode || t("common.unavailable")}</span> | ${t("proxy.envFile")}: ${proxy.env_exists ? t("common.present") : t("common.missing")}</div>
    ${data.system_proxy_allowed ? "" : `<div class="warn">${t("proxy.disabledInTun")}</div>`}
  `;
  document.getElementById("proxy-enable").disabled = !data.system_proxy_allowed;
  document.getElementById("proxy-apply").disabled = !data.system_proxy_allowed;
  document.getElementById("proxy-hint").innerHTML =
    `${t("proxy.serverShell")}: <code>source ${proxy.env_file}</code><br>` +
    `${t("proxy.cli")}: <code>clashtx mode system</code> / <code>clashtx mode tun</code>`;
}

async function loadSubscriptions() {
  const rows = await api("/api/subscriptions");
  const tbody = document.querySelector("#sub-table tbody");
  tbody.innerHTML = "";
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.dataset.name = row.name;
    tr.innerHTML = `
      <td class="col-active">${row.active ? "🟢" : ""}</td>
      <td>${escapeHtml(row.name)}</td>
      <td>${escapeHtml(formatShanghaiTime(row.updated_at))}</td>
      <td>${escapeHtml(row.url)}</td>
    `;
    tr.addEventListener("click", () => selectSubscriptionRow(tr, row));
    if (state.selectedSub === row.name) tr.classList.add("selected");
    tbody.appendChild(tr);
  });
}

function selectSubscriptionRow(tr, row) {
  document.querySelectorAll("#sub-table tbody tr").forEach((el) => el.classList.remove("selected"));
  tr.classList.add("selected");
  state.selectedSub = row.name;
  document.getElementById("sub-name").value = row.name;
  document.getElementById("sub-url").value = row.url;
}

async function loadNodes() {
  const data = await api("/api/nodes");
  state.nodeData = data;
  state.activeNodeGroup = data.active_group;
  document.getElementById("mode-select").value = data.mode;
  document.getElementById("sort-select").value = data.sort_mode;
  renderGroupList();
  renderNodeTable(state.activeNodeGroup);
}

function renderGroupList() {
  const container = document.getElementById("group-list");
  container.innerHTML = "";
  if (!state.nodeData) return;
  state.nodeData.groups
    .filter((group) => group.nodes.length > 0)
    .forEach((group) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `group-item${group.name === state.activeNodeGroup ? " active" : ""}`;
      button.innerHTML = `
        <div class="group-item-name">${escapeHtml(group.name)}</div>
        <div class="group-item-meta">${escapeHtml(group.type)} · ${group.nodes.length} ${t("nodes.nodes")}${group.selectable ? "" : ` · ${t("common.auto")}`}</div>
        <div class="group-item-now">${escapeHtml(noneText(group.now))}</div>
      `;
      button.addEventListener("click", () => selectNodeGroup(group.name));
      container.appendChild(button);
    });
}

function renderNodeTable(groupName) {
  const summary = document.getElementById("group-summary");
  const tbody = document.querySelector("#node-table tbody");
  tbody.innerHTML = "";
  if (!state.nodeData || !groupName) {
    summary.textContent = t("nodes.noGroups");
    return;
  }
  const group = state.nodeData.groups.find((item) => item.name === groupName);
  if (!group) {
    summary.textContent = t("nodes.selectGroup");
    return;
  }
  summary.textContent =
    `${t("nodes.group")}: ${group.name} | ${t("nodes.type")}: ${group.type} | ` +
    `${group.selectable ? t("common.manual") : t("common.auto")} | ${t("nodes.active")}: ${group.now || t("common.none")}`;
  group.nodes.forEach((row) => {
    const tr = document.createElement("tr");
    tr.dataset.group = group.name;
    tr.dataset.node = row.node;
    tr.innerHTML = `
      <td>${escapeHtml(row.node)}</td>
      <td>${formatDelayCell(row.delay)}</td>
    `;
    if (row.selected) tr.classList.add("selected");
    tr.addEventListener("click", () => selectNodeRow(tr, { group: group.name, node: row.node }));
    if (
      state.selectedNode &&
      state.selectedNode.group === group.name &&
      state.selectedNode.node === row.node
    ) {
      tr.classList.add("selected");
    }
    tbody.appendChild(tr);
  });
}

async function selectNodeGroup(groupName) {
  state.activeNodeGroup = groupName;
  state.selectedNode = null;
  renderGroupList();
  renderNodeTable(groupName);
  try {
    await api("/api/nodes/group", {
      method: "POST",
      body: JSON.stringify({ group: groupName }),
    });
  } catch (_) {
    /* keep local selection even if persistence fails */
  }
}

function selectNodeRow(tr, row) {
  document.querySelectorAll("#node-table tbody tr").forEach((el) => el.classList.remove("selected"));
  tr.classList.add("selected");
  state.selectedNode = { group: row.group, node: row.node };
}

function delayClass(delay) {
  if (delay == null) return "delay-none";
  if (delay < 0) return "delay-bad";
  if (delay <= 150) return "delay-good";
  if (delay <= 400) return "delay-ok";
  return "delay-bad";
}

function formatDelayCell(delay) {
  if (delay == null) return '<span class="delay-none">-</span>';
  return `<span class="${delayClass(delay)}">${escapeHtml(String(delay))}</span>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function refreshTab(tab = state.tab) {
  if (tab === "dashboard") {
    await loadDashboard();
    await loadTraffic();
  } else if (tab === "proxy") {
    await loadProxy();
  } else if (tab === "subscriptions") {
    await loadSubscriptions();
  } else if (tab === "nodes") {
    await loadNodes();
  }
}

function switchTab(tab) {
  state.tab = tab;
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  document.querySelectorAll(".tab").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `tab-${tab}`);
  });
  document.getElementById("page-title").textContent = t(`title.${tab}`);
  refreshTab(tab).catch((err) => toast(err.message, true));
}

document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

document.getElementById("lang-toggle").addEventListener("click", () => {
  setLanguage(state.lang === "en" ? "zh" : "en");
});

document.getElementById("theme-toggle").addEventListener("click", () => {
  setTheme(state.theme === "dark" ? "light" : "dark");
});

document.getElementById("refresh-btn").addEventListener("click", () => {
  refreshTab().then(() => toast(t("toast.refreshed"))).catch((err) => toast(err.message, true));
});

document.querySelectorAll("[data-action='service']").forEach((btn) => {
  btn.addEventListener("click", async () => {
    try {
      await api(`/api/service/${btn.dataset.value}`, { method: "POST" });
      toast(t(`toast.service.${btn.dataset.value}`));
      await refreshTab("dashboard");
    } catch (err) {
      toast(err.message, true);
    }
  });
});

document.getElementById("proxy-apply").addEventListener("click", async () => {
  try {
    const payload = {
      host: document.getElementById("proxy-host").value,
      port: Number(document.getElementById("proxy-port").value),
      no_proxy: document.getElementById("proxy-no-proxy").value,
    };
    await api("/api/proxy/apply", { method: "POST", body: JSON.stringify(payload) });
    toast(t("toast.proxyApplied"));
    await loadProxy();
  } catch (err) {
    toast(err.message, true);
  }
});

document.getElementById("proxy-enable").addEventListener("click", async () => {
  try {
    await api("/api/proxy/enable", { method: "POST" });
    toast(t("toast.proxyEnabled"));
    await loadProxy();
  } catch (err) {
    toast(err.message, true);
  }
});

document.getElementById("proxy-disable").addEventListener("click", async () => {
  try {
    await api("/api/proxy/disable", { method: "POST" });
    toast(t("toast.proxyDisabled"));
    await loadProxy();
  } catch (err) {
    toast(err.message, true);
  }
});

document.getElementById("proxy-refresh").addEventListener("click", () => {
  loadProxy().then(() => toast(t("toast.networkRefreshed"))).catch((err) => toast(err.message, true));
});

async function setNetworkMode(mode) {
  try {
    await api("/api/network/mode", {
      method: "POST",
      body: JSON.stringify({ mode }),
    });
    toast(t("toast.networkMode", { mode }));
    await loadProxy();
    if (state.tab === "dashboard") await loadDashboard();
  } catch (err) {
    toast(err.message, true);
  }
}

document.getElementById("mode-system").addEventListener("click", () => setNetworkMode("system"));
document.getElementById("mode-tun").addEventListener("click", () => setNetworkMode("tun"));

document.getElementById("sub-save").addEventListener("click", async () => {
  const name = document.getElementById("sub-name").value.trim();
  const url = document.getElementById("sub-url").value.trim();
  if (!name || !url) return toast(t("toast.nameUrlRequired"), true);
  try {
    const data = await api("/api/subscriptions", {
      method: "POST",
      body: JSON.stringify({ name, url }),
    });
    toast(t("toast.subscriptionSaved", { name: data.name }));
    state.selectedSub = data.name;
    await loadSubscriptions();
  } catch (err) {
    toast(err.message, true);
  }
});

document.getElementById("sub-activate").addEventListener("click", async () => {
  if (!state.selectedSub) return toast(t("toast.selectSubscription"), true);
  try {
    await api(`/api/subscriptions/${encodeURIComponent(state.selectedSub)}/activate`, {
      method: "POST",
    });
    toast(t("toast.subscriptionActivated", { name: state.selectedSub }));
    await loadSubscriptions();
    await loadDashboard();
  } catch (err) {
    toast(err.message, true);
  }
});

document.getElementById("sub-update").addEventListener("click", async () => {
  if (!state.selectedSub) return toast(t("toast.selectSubscription"), true);
  try {
    await api(`/api/subscriptions/${encodeURIComponent(state.selectedSub)}/refresh`, {
      method: "POST",
    });
    toast(t("toast.subscriptionUpdated", { name: state.selectedSub }));
    await loadSubscriptions();
  } catch (err) {
    toast(err.message, true);
  }
});

document.getElementById("sub-update-all").addEventListener("click", async () => {
  const progressEl = document.getElementById("sub-update-progress");
  const button = document.getElementById("sub-update-all");
  const rows = await api("/api/subscriptions").catch((err) => {
    toast(err.message, true);
    return null;
  });
  if (!rows) return;
  if (!rows.length) {
    progressEl.textContent = t("subscriptions.updateEmpty");
    toast(t("subscriptions.updateEmpty"), "info");
    return;
  }

  button.disabled = true;
  const total = rows.length;
  const successful = [];
  const failed = [];
  const lines = [];

  try {
    for (const [index, row] of rows.entries()) {
      const done = index + 1;
      progressEl.textContent = [
        ...lines,
        t("subscriptions.updateProgress", { done, total, name: row.name }),
      ].join(" | ");
      try {
        await api(`/api/subscriptions/${encodeURIComponent(row.name)}/refresh`, {
          method: "POST",
        });
        successful.push(row.name);
        lines.push(t("subscriptions.updateOk", { done, total, name: row.name }));
      } catch (err) {
        failed.push({ name: row.name, error: err.message });
        lines.push(
          t("subscriptions.updateFailed", {
            done,
            total,
            name: row.name,
            error: err.message,
          }),
        );
      }
      progressEl.textContent = lines.join(" | ");
      await loadSubscriptions();
    }
    await loadSubscriptions();
    await loadDashboard();
    const failures = failed.length
      ? `\n${failed.map((item) => `${item.name}: ${item.error}`).join("\n")}`
      : "";
    toast(
      `${t("toast.subscriptionUpdateAll", {
        success: successful.length,
        failed: failed.length,
      })}${failures}`,
      failed.length ? "info" : "success",
    );
  } catch (err) {
    toast(err.message, true);
  } finally {
    button.disabled = false;
  }
});

document.getElementById("sub-delete").addEventListener("click", async () => {
  if (!state.selectedSub) return toast(t("toast.selectSubscription"), true);
  try {
    await api(`/api/subscriptions/${encodeURIComponent(state.selectedSub)}`, {
      method: "DELETE",
    });
    toast(t("toast.subscriptionDeleted", { name: state.selectedSub }));
    state.selectedSub = null;
    await loadSubscriptions();
  } catch (err) {
    toast(err.message, true);
  }
});

document.getElementById("mode-select").addEventListener("change", async (event) => {
  try {
    await api("/api/mode", {
      method: "POST",
      body: JSON.stringify({ mode: event.target.value }),
    });
    toast(t("toast.proxyMode", { mode: event.target.value }));
  } catch (err) {
    toast(err.message, true);
  }
});

document.getElementById("sort-select").addEventListener("change", async (event) => {
  try {
    await api("/api/sort", {
      method: "POST",
      body: JSON.stringify({ sort_mode: event.target.value }),
    });
    await loadNodes();
  } catch (err) {
    toast(err.message, true);
  }
});

document.getElementById("nodes-refresh").addEventListener("click", () => {
  loadNodes().then(() => toast(t("toast.nodesRefreshed"))).catch((err) => toast(err.message, true));
});

document.getElementById("node-select").addEventListener("click", async () => {
  if (!state.selectedNode) return toast(t("toast.selectNode"), true);
  try {
    await api("/api/nodes/select", {
      method: "POST",
      body: JSON.stringify(state.selectedNode),
    });
    toast(t("toast.nodeSelected"));
    await loadNodes();
    await loadDashboard();
  } catch (err) {
    toast(err.message, true);
  }
});

document.getElementById("node-test").addEventListener("click", async () => {
  if (!state.selectedNode) return toast(t("toast.selectNode"), true);
  try {
    const data = await api("/api/nodes/test", {
      method: "POST",
      body: JSON.stringify({ node: state.selectedNode.node }),
    });
    toast(t("toast.delay", { node: data.node, delay: data.delay }));
    await loadNodes();
  } catch (err) {
    toast(err.message, true);
  }
});

document.getElementById("node-test-all").addEventListener("click", () => {
  startTestAllNodes();
});

async function startTestAllNodes() {
  const progressEl = document.getElementById("test-all-progress");
  const button = document.getElementById("node-test-all");
  button.disabled = true;
  progressEl.textContent = t("test.start");
  try {
    await api("/api/nodes/test-all/start", { method: "POST" });
  } catch (err) {
    button.disabled = false;
    progressEl.textContent = "";
    toast(err.message, true);
    return;
  }

  const poll = async () => {
    const status = await api("/api/nodes/test-all/status");
    if (status.running) {
      const current = status.current || "...";
      progressEl.textContent = t("test.running", {
        done: status.done,
        total: status.total,
        current,
      });
      return false;
    }
    if (status.error) {
      progressEl.textContent = "";
      toast(status.error, true);
      return true;
    }
    if (status.result) {
      const result = status.result;
      const delayText = result.fastest_delay != null ? ` (${result.fastest_delay} ms)` : "";
      const message = t("test.complete", {
        tested: result.tested,
        total: result.total,
        failed: result.failed,
        fastest: result.fastest || t("common.none"),
        delay: delayText,
      });
      progressEl.textContent = message;
      toast(message);
      await loadNodes();
      await loadDashboard();
    }
    return true;
  };

  while (true) {
    await new Promise((resolve) => setTimeout(resolve, 300));
    try {
      if (await poll()) break;
    } catch (err) {
      progressEl.textContent = "";
      toast(err.message, true);
      break;
    }
  }
  button.disabled = false;
}

function startTrafficPolling() {
  if (state.trafficTimer) clearInterval(state.trafficTimer);
  state.trafficTimer = setInterval(() => {
    if (state.tab === "dashboard") loadTraffic();
  }, 1500);
}

applyTheme();
applyTranslations();
switchTab("dashboard");
startTrafficPolling();
