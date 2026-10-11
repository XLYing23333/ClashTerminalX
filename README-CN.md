<div align="center">

<img src="asset/LOGO.png" alt="ClashTX" width="240" style="border-radius: 18px;" />

# ClashTX

**ClashTerminalX** — 面向 Linux 的终端优先 Mihomo/Clash 管理工具。

<p align="center">
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white" alt="Python" />
  </a>
  <a href="https://kernel.org/">
    <img src="https://img.shields.io/badge/Platform-Linux-1793D2?logo=linux&logoColor=white" alt="Platform" />
  </a>
  <a href="https://github.com/MetaCubeX/mihomo">
    <img src="https://img.shields.io/badge/Core-Mihomo-61afef" alt="Mihomo" />
  </a>
  <a href="https://github.com/Textualize/textual">
    <img src="https://img.shields.io/badge/TUI-Textual-528bff" alt="Textual" />
  </a>
</p>

通过 **Textual TUI**、**FastAPI Web UI** 或轻量 **CLI**，管理订阅、代理组、延迟测试、系统代理与 TUN 模式。

[English](./README.md) | **简体中文**

</div>

---

## 功能特性

| 功能 | 描述 |
| --- | --- |
| **仪表盘** | 服务状态、实时流量、核心版本 |
| **订阅** | 添加、更新、激活、删除 Mihomo YAML 订阅 |
| **节点** | 代理组选择、延迟排序、单节点 / 批量测速 |
| **代理** | 系统代理（GNOME + Shell 环境变量）与 Mihomo 混合端口设置 |
| **网络模式** | **System**（系统代理）与 **TUN**（全局隧道），互斥切换 |
| **界面** | Textual TUI · Web UI（`:7887`）· CLI 自动化 |

运行时数据默认存放在 `.runtime/`，与 Clash Verge 及其他本地 Clash 客户端隔离。首次启动时会自动把 `vendor/geodata/` 中的 GeoIP / GeoSite 数据库复制到配置目录，避免从 GitHub 下载失败。

---

## 快速开始

```bash
git clone https://github.com/XLYing23333/ClashTerminalX.git ClashTX
cd ClashTX

./scripts/install.sh
sudo ./clashtx.sh help
sudo ./clashtx.sh start
sudo ./clashtx.sh          # 打开 TUI
sudo ./clashtx.sh ui       # 打开 Web UI：http://127.0.0.1:7887
```

安装脚本会创建 `.venv`、安装依赖，并在仓库根目录生成 `clashtx.sh`。

---

## 终端 TUI

启动终端界面：

```bash
sudo ./clashtx.sh
```

TUI 适合键盘优先的服务器使用场景。你可以在这里查看服务状态和实时流量、管理订阅、切换代理组、执行节点延迟测试，并切换 System / TUN 网络模式。

![ClashTX 终端 TUI](asset/img-terminal.png)

常用快捷键：

- `r` 刷新仪表盘、代理和节点数据。
- `s` 启动 Mihomo 核心。
- `x` 停止 Mihomo 核心。
- `q` 退出 TUI。

---

## Web UI

启动浏览器界面：

```bash
sudo ./clashtx.sh ui
```

然后打开 [http://127.0.0.1:7887](http://127.0.0.1:7887)。如果需要绑定到其他地址或端口，可以使用 `--host` 和 `--port`：

```bash
sudo ./clashtx.sh ui --host 0.0.0.0 --port 7887
```

Web UI 提供与 TUI 相同的核心控制能力，并支持 EN / 简体中文双语切换、深色 / 浅色模式、订阅管理、代理模式控制、节点测速和实时流量图表。

![ClashTX Web UI](asset/img-webui.png)

---


### Web 登录与修改密码

默认访问地址为 `http://127.0.0.1:7887`，首次登录密码为 **`7897`**。页面支持 EN / 简体中文登录与退出。全部管理 API、API 文档与 OpenAPI 都需要登录；会话有效期为 12 小时，服务重启或密码更改后旧会话失效。

永久修改密码并启动 Web UI：

```bash
sudo ./clashtx.sh ui --password '你的新密码'
```

后续不带 `--password` 启动时沿用已保存的密码；重置密码也使用此参数。修改前请停止已有 Web 服务，再使用上述命令重启。认证文件只保存带随机盐的密码哈希，与 Mihomo 控制密钥分别存储，不会提交到 GitHub。

Web 默认只监听本机。远程访问可使用 SSH 转发：

```bash
ssh -L 7887:127.0.0.1:7887 user@server
```

也可以显式绑定 `--host 0.0.0.0`；远程开放前请修改默认密码，并通过 HTTPS 反向代理保护密码与会话。登录错误每个 IP 每分钟最多 5 次，修改操作需要 CSRF 令牌。

反向代理连接本机监听的 Web 服务时，请传递本机 Host（例如 `proxy_set_header Host 127.0.0.1;`），以通过 DNS 重绑定防护。

---

## 命令一览

| 命令 | 说明 |
| --- | --- |
| `sudo ./clashtx.sh` | 启动 Textual TUI |
| `sudo ./clashtx.sh ui [--host HOST] [--port PORT]` | 启动 Web UI（默认 `127.0.0.1:7887`；`--password` 修改密码） |
| `sudo ./clashtx.sh start` | 启动 Mihomo 核心 |
| `sudo ./clashtx.sh stop` | 停止 Mihomo 核心 |
| `sudo ./clashtx.sh restart` | 重启 Mihomo 核心 |
| `sudo ./clashtx.sh status` | 查看服务状态 |
| `sudo ./clashtx.sh mode system` | 系统代理模式（关闭 TUN，启用代理） |
| `sudo ./clashtx.sh mode tun` | TUN 模式（关闭系统代理） |
| `source ./clashtx.sh source` | 在当前 Shell 加载 `proxy.env` |
| `source ./clashtx.sh start` | 启动核心并自动加载 `proxy.env` |
| `source ./clashtx.sh restart` | 重启核心并自动加载 `proxy.env` |
| `sudo ./clashtx.sh help` | 显示帮助 |

---

## 网络模式

### System 模式

- 关闭 TUN 并重新生成 `mihomo.yaml`
- 自动启用系统代理（GNOME + `proxy.env`）
- 适合遵循系统 / Shell 代理设置的应用

### TUN 模式

- 关闭系统代理，并在配置中启用 Mihomo TUN
- 需要 `/dev/net/tun` 以及 Mihomo 二进制文件的 **CAP_NET_ADMIN** 权限

一次性配置：

```bash
./vendor/tun/grant-caps.sh
# 或
sudo setcap cap_net_admin,cap_net_bind_service+ep vendor/mihomo/verge-mihomo
```

替换 Mihomo 二进制文件后需重新授权。TUN 辅助脚本位于 `vendor/tun/`。

---

## 项目结构

```
ClashTX/
├── asset/LOGO.png          # 品牌 Logo（源文件）
├── asset/img-terminal.png  # 终端 TUI 截图
├── asset/img-webui.png     # Web UI 截图
├── clashtx.sh              # 入口脚本（由 scripts/clashtx-entry.sh 复制）
├── scripts/install.sh
├── src/clashtx/            # 应用源码
│   ├── tui/                # Textual TUI
│   ├── web/                # FastAPI + 静态 Web UI
│   ├── controller.py       # 共享业务逻辑
│   └── system/             # 服务、代理、TUN、网络
├── vendor/
│   ├── mihomo/             # 内置 Mihomo 核心
│   ├── geodata/            # 内置 GeoIP / GeoSite 数据库
│   └── tun/                # TUN 配置脚本
└── .runtime/               # 配置、日志、PID（默认）
```

默认混合代理端口：**7897**（与 Clash Verge 对齐）。

---

## 配置

可通过环境变量覆盖运行时目录：

| 变量 | 用途 |
| --- | --- |
| `CLASHTX_CONFIG_DIR` | 配置与订阅 |
| `CLASHTX_DATA_DIR` | 核心数据 |
| `CLASHTX_CACHE_DIR` | 日志与 PID 文件 |
| `CLASHTX_CORE_PATH` | 自定义 Mihomo 二进制路径 |
| `CLASHTX_TUN_DIR` | 自定义 TUN 工具目录 |

---


## 核心隔离与升级兼容

- 新安装默认 Mihomo 控制地址为 `127.0.0.1:19090`，首次启动生成独立随机密钥；混合代理端口仍为 `7897`。已有显式控制地址保留，控制地址仅允许本机 IP 或 `localhost`。
- 停止、重启与 API 操作验证核心 PID、启动时间、可执行文件、运行用户、配置参数和控制接口归属；不会接管其他代理。端口被占用或身份无法验证时拒绝操作。
- 旧 PID 文件只有在核心身份完整验证后才会被采纳。升级不会自动重启已有核心；旧核心需要用户主动重启，才能启用新的后台日志限制。身份异常时先核实进程，避免盲目删除 PID 文件。
- 订阅采用独立 UUID 文件名，支持中文名称。首次修改旧订阅时自动备份并迁移；发现多个订阅共享旧文件，会提示逐一更新订阅。迁移保留现存内容，不会自动下载，也无法恢复此前被覆盖的历史内容。
- 配置、认证、运行身份与代理环境文件采用私有权限和原子写入；共享配置操作使用文件锁。全局脚本仍可调整规则等配置，但控制地址、控制密钥和日志级别由 ClashTX 管理。

## 后台日志与故障节点

核心由独立后台运行器启动，运行器持续收集 stdout / stderr。关闭 TUI、Web 页面或退出启动命令后，日志限制仍持续生效：

- 当前 `mihomo.log` 最大 **20 MiB**。
- 最多保留 **3** 个备份，每个最大 **20 MiB**，总量不超过 **80 MiB**。
- 启动及订阅热加载统一使用 `warning`。坏节点的连接失败仍会留下警告，但日志不再无限增长。
- 磁盘写入失败时丢弃无法保存的数据并继续读取核心输出，避免因日志写入错误阻塞代理；磁盘恢复后继续记录。

手动清理日志（不停止核心）：

```bash
sudo ./clashtx.sh logs clean
```

日志轮转限制磁盘占用，不会自动替换手动选择的坏节点。请在 Nodes 页面切换到健康节点，或在订阅配置中使用自动选择 / 故障转移组。

## 隔离测试

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest -q
```

测试使用临时运行目录、进程内 Web 客户端、合成日志和模拟核心。隔离层拦截真实核心启动、进程信号、网络连接、桌面代理设置及权限工具，不修改已有代理。

---

## 许可证

ClashTX 使用 **GNU General Public License v3.0** 发布。详见 [LICENSE](./LICENSE)。

