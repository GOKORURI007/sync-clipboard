# Sync Clipboard

![GitHub License](https://img.shields.io/github/license/GOKORURI007/sync-clipboard?link=https%3A%2F%2Fgithub.com%2FGOKORURI007%2Fsync-clipboard%2Fblob%2Fmaster%2FLICENSE)

[English](../README.md) | [简体中文](./README-zhCN.md)

Sync Clipboard 是一个跨平台剪贴板同步软件，理论上可以在所有pyperclip支持的平台上实现同步。开发这个软件是因为Deskflow、Barrier等键鼠共享软件的功能时灵时不灵。

支持的平台：

- [x] windows
- [x] Linux/Xserver
- [x] Linux/Wayland
- [ ] MacOS (未测试，但应该可以，欢迎报告)

支持的功能：

- [x] 剪贴板文本同步
- [ ] 剪贴板图像同步
- [ ] 剪贴板文件同步

## 安装

### Release

从 [Release](https://github.com/GOKORURI007/sync-clipboard/releases) 处下载。

### Scoop (Windows 推荐)

```powershell
# 1. 添加 bucket
scoop bucket add ruri-scoop "https://github.com/gokoruri007/ruri-scoop"
# 2. 安装 sync-clipboard
scoop install ruri-scoop/sync-clipboard-gui

# 3. 安装 cli 版本 (可选)
scoop install ruri-scoop/sync-clipboard-cli
```

### 从源代码构建

```powershell
# 1. 克隆仓库
git clone https://github.com/GOKORURI007/sync-clipboard.git
cd sync-clipboard

# 2. 直接运行 python 模块 (可选)
uv run python -m sync_clipboard-gui
# 或者
uv run python -m sync_clipboard-cli

# 3. PyInstaller 打包 (可执行文件在 exe 目录下)
uv run pyinstaller .\sync-clipboard-gui.spec
uv run pyinstaller .\sync-clipboard-cli.spec
```

### Nix/Flake (NixOS 推荐)

在你的 `flake.nix` 中添加 `input`:

```nix
# flake.nix
{
    inputs = {
        # 1. 定义上游源
        nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";

        sync-clipboard = {
          url = "github:GOKORURI007/sync-clipboard";
          inputs.nixpkgs.follows = "nixpkgs";
        };
    };
    # ...
}
```

在你的配置中引入 sync-clipboard:

```nix
{
    environment.systemPackages = with pkgs; [
        inputs.sync-clipboard.packages.${stdenv.hostPlatform.system}.default

        # 根据需要添加
        wl-clipboard # wayland 依赖
        x-clip # xserver 依赖
    ];
}
```

可以通过 systemd 运行:

```ini
[Service]
Environment=PATH=/run/current-system/sw/bin:/etc/profiles/per-user/[your-username]/bin
ExecStart=sync-clipboard --mode client --host 192.168.123.154
ImportCredential=true
Restart=no

[Unit]
After=graphical-session.target
Description=Sync Clipboard
PartOf=graphical-session.target
```

### 开发文档

#### 开发环境

请先安装 [uv](https://github.com/astral-sh/uv)

```bash
# 克隆此仓库
git clone https://github.com/GOKORURI007/sync-clipboard.git
cd sync-clipboard

# 初始化环境
uv sync

# 开始开发 ...
```

### 项目结构

```
.
├── docs/             # 文档文件
├── assets/           # 图标资源
├── scripts/          # 实用脚本
│   ├── format.py     # 代码格式化脚本
│   ├── release.py    # 发布和版本管理脚本
│   └── run_tests.py  # 测试运行器脚本
├── src               # 主要代码
├── pyproject.toml    # 项目配置
└── uv.lock           # 依赖锁定文件
```


