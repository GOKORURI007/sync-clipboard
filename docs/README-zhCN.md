# Sync Clipboard | 跨设备剪贴板同步工具

![GitHub License](https://img.shields.io/github/license/GOKORURI007/sync-clipboard?link=https%3A%2F%2Fgithub.com%2FGOKORURI007%2Fsync-clipboard%2Fblob%2Fmaster%2FLICENSE)
![Python Version](https://img.shields.io/badge/python-3.13%2B-blue)

[English](../README.md) | [简体中文](./README-zhCN.md)

Sync Clipboard 是一款基于 WebSocket 技术的跨平台剪贴板实时同步工具，采用标准的 Server-Client
架构设计，用于解决 [Deskflow](https://github.com/deskflow/deskflow) 等键鼠共享软件剪贴板功能不稳定的问题。

## 📋 功能支持矩阵

| 功能类别          | 状态     | 说明                                                           |
|---------------|--------|--------------------------------------------------------------|
| 文本同步          | ✅ 已支持  | 支持纯文本和富文本内容                                                  |
| 图像同步          | ⏳ 暂无计划 | 取决于 [pyperclip](https://github.com/asweigart/pyperclip) 是否支持 |
| 文件同步          | ⏳ 暂无计划 | 取决于 [pyperclip](https://github.com/asweigart/pyperclip) 是否支持 |
| Windows       | ✅ 已支持  | 完整功能支持                                                       |
| Linux/X11     | ✅ 已支持  | 通过 X11 剪贴板 API                                               |
| Linux/Wayland | ✅ 已支持  | 通过 wl-clipboard 工具                                           |
| macOS         | ⏳ 未测试  | 理论支持，欢迎测试反馈                                                  |

## 🚀 快速开始

### 📦 安装方式

#### 🔧 发行版安装 (Windows & Linux & MacOS)

从 [GitHub Release](https://github.com/GOKORURI007/sync-clipboard/releases) 页面下载对应平台的预编译版本。

#### 💻 Scoop 包管理器 (Windows 推荐)

```powershell
# 1. 添加自定义 bucket
scoop bucket add ruri-scoop "https://github.com/gokoruri007/ruri-scoop"

# 2. 安装图形界面版本（推荐）
scoop install ruri-scoop/sync-clipboard-gui

# 3. 安装命令行版本（可选）
scoop install ruri-scoop/sync-clipboard-cli
```

#### 🛠️ 从源码构建 (Windows & Linux & MacOS)

```bash
# 1. 克隆项目
git clone https://github.com/GOKORURI007/sync-clipboard.git
cd sync-clipboard

# 2. 安装依赖（推荐使用 uv）
uv sync

# 3. 直接运行模块
uv run python -m src.sync_clipboard_cli --mode server --host 0.0.0.0 --port 8765
# 或者启动图形界面
uv run python -m src.sync_clipboard_gui

# 4. 打包为可执行文件
uv run pyinstaller sync-clipboard-cli.spec
uv run pyinstaller sync-clipboard-gui.spec
```

### 🧊 Nix/Flake (NixOS 推荐)

在您的 `flake.nix` 中添加配置：

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    sync-clipboard = {
      url = "github:GOKORURI007/sync-clipboard";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {self, nixpkgs, sync-clipboard, ...}:
  {
    nixosConfigurations.your-hostname = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        {
          environment.systemPackages = with nixpkgs.legacyPackages.x86_64-linux; [
            sync-clipboard.packages.x86_64-linux.default
            wl-clipboard  # Wayland 支持
            xclip         # X11 支持
          ];
        }
      ];
    };
  };
}
```

通过 systemd 服务运行：

```ini
[Unit]
Description = Sync Clipboard Service
After = graphical-session.target
PartOf = graphical-session.target

[Service]
Type = simple
Environment = PATH=/run/current-system/sw/bin
ExecStart = sync-clipboard --mode client --host 192.168.1.100 --port 8765
Restart = always
RestartSec = 5

[Install]
WantedBy = graphical-session.target
```

## 🎯 使用指南

### 🖥️ 命令行模式

** 服务端启动：**

```bash
# 监听所有网络接口
sync-clipboard --mode server --host 0.0.0.0 --port 8765

# 仅监听本地回环
sync-clipboard --mode server --host 127.0.0.1 --port 8765
```

** 客户端连接：**

```bash
# 连接到远程服务器
sync-clipboard --mode client --host 192.168.1.100 --port 8765

# 使用自定义主机名标识
sync-clipboard --mode client --host server.local --port 8765 --hostname my-laptop
```

** 命令行命令：**

### 🖱️ 图形界面模式

启动图形界面：

```bash
sync-clipboard-gui
```

### ⚙️ 高级配置

配置文件位于：

- **Windows**: `%APPDATA%/sync-clipboard/config.json`
- **Linux/macOS**: `~/.config/sync-clipboard/config.json`

示例配置：

```json
{
    "mode": "client",
    "host": "192.168.1.100",
    "port": 8765,
    "hostname": "my-workstation",
    "minimize_on_close": true
}
```

## 🏗️ 技术架构

### 📊 系统架构

```
┌─────────────────┐    WebSocket    ┌─────────────────┐
│   SyncServer    │◄───────────────►│   SyncClient    │
│  (中央枢纽节点)  │                 │   (终端节点)     │
└─────────────────┘                 └─────────────────┘
         │                                   │
         ▼                                   ▼
┌─────────────────┐                 ┌─────────────────┐
│ ClipboardMonitor│                 │ ClipboardMonitor│
│   (本地监听器)   │                 │   (本地监听器)   │
└─────────────────┘                 └─────────────────┘
```

### 📁 项目结构

```
sync-clipboard/
├── src/                             # 源代码目录
│   ├── core/                        # 核心模块
│   │   ├── clipboard.py             # 剪贴板操作核心
│   │   ├── protocol.py              # 通信协议定义
│   │   ├── config.py                # 配置管理
│   │   └── exceptions.py            # 异常定义
│   ├── server/                      # 服务端实现
│   │   └── sync_server.py           # WebSocket 服务端
│   ├── client/                      # 客户端实现
│   │   └── sync_client.py           # WebSocket 客户端
│   ├── compat/                      # 兼容性层
│   ├── sync_clipboard_cli.py        # 命令行接口
│   └── sync_clipboard_gui.py        # 图形界面
├── tests/                           # 测试套件
│   ├── test_integration.py          # 集成测试
│   └── test_anti_loop_properties.py # 防回环属性测试
├── scripts/                         # 开发辅助脚本
│   ├── format.py                    # 代码格式化
│   ├── release.py                   # 版本发布
│   └── test_all.py                  # 测试运行器
├── assets/                          # 资源文件
├── docs/                            # 文档资料
├── pyproject.toml                   # 项目配置
└── README.md                        # 英文文档
```

## 👨‍💻 开发指南

### 🛠️ 开发环境搭建

```bash
# 1. 克隆项目
git clone https://github.com/GOKORURI007/sync-clipboard.git
cd sync-clipboard

# 2. 安装依赖管理工具
# 推荐使用 uv (https://github.com/astral-sh/uv)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. 初始化开发环境
uv sync

# 4. 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows
```

### 🧪 运行测试

```bash
uv run python scripts/test_all.py
```

### 🎨 代码质量

```bash
# 代码格式化
uv run python scripts/format.py
```

### 🚀 构建发布

```bash
# 创建新版本
uv run python scripts/release.py

# 打包可执行文件
uv run pyinstaller sync-clipboard-cli.spec
uv run pyinstaller sync-clipboard-gui.spec
```

## 🤝 贡献指南

我们欢迎任何形式的贡献！

### 📝 贡献流程

1. Fork 项目仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 格式化代码： `uv run python scripts/format.py`
4. 提交更改：`git commit -am 'Add some feature'`
5. 推送分支：`git push origin feature/your-feature`
6. 创建 Pull Request

### 🎯 开发规范

- 遵循 [PEP 8](https://peps.python.org/pep-0008/) 代码风格
- 更新相关文档和注释
- 使用类型提示增强代码可读性
- 保持提交信息清晰明确

### 🐛 报告问题

请在 [Issues](https://github.com/GOKORURI007/sync-clipboard/issues) 中报告问题，包含：

- 使用的操作系统和版本
- Sync Clipboard 版本
- 详细的错误描述和重现步骤
- 相关的日志输出

## 📄 许可证

本项目采用 MIT
许可证，详情请参见 [LICENSE](https://github.com/GOKORURI007/sync-clipboard/blob/master/LICENSE) 文件。

## 🙏 致谢

感谢以下开源项目的支持：

- [websockets](https://github.com/aaugustin/websockets) - WebSocket 实现
- [pyperclip](https://github.com/asweigart/pyperclip) - 跨平台剪贴板操作
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) - 现代化 GUI 框架
- [pystray](https://github.com/moses-palmer/pystray) - 系统托盘支持

## 📞 联系方式

- 项目主页：[GitHub Repository](https://github.com/GOKORURI007/sync-clipboard)
- 问题反馈：[Issue Tracker](https://github.com/GOKORURI007/sync-clipboard/issues)


