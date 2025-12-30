# SyncClipboard | 剪贴板同步工具

[English](#english) | [中文](#中文)

---

## 中文

通过WebSocket在不同操作系统之间实时同步剪贴板内容的工具。采用标准的Server-Client架构，提供稳定可靠的跨设备剪贴板同步体验。

### 功能特点

- 🚀 **实时同步** - 基于WebSocket实现毫秒级剪贴板同步
- 🔄 **防回环机制** - 智能防止剪贴板内容无限循环同步
- 🖥️ **跨平台支持** - 支持Windows和Linux操作系统
- 🔌 **自动重连** - 客户端断线后自动重连，确保服务稳定性
- 🎛️ **双界面模式** - 提供命令行和图形界面两种使用方式
- ⚙️ **灵活配置** - 支持自定义IP地址、端口和主机名
- 📦 **便携部署** - 支持打包为独立可执行文件

### 快速开始

#### 安装依赖

使用 `uv` (推荐):
```bash
uv sync
```

或使用 `pip`:
```bash
pip install websockets click pyperclip customtkinter pystray pillow
```

#### 基本使用

1. **启动服务器** (在主机上):
   ```bash
   uv run python -m src.sync_clipboard --mode server --host 0.0.0.0 --port 8765
   ```

2. **连接客户端** (在其他设备上):
   ```bash
   uv run python -m src.sync_clipboard --mode client --host <服务器IP> --port 8765
   ```

3. **使用图形界面**:
   ```bash
   uv run python -m src.sync_clipboard_gui
   ```

### 详细使用指南

#### 命令行模式

**服务器模式参数:**
- `--mode server` - 启动服务器模式
- `--host 0.0.0.0` - 监听所有网络接口
- `--port 8765` - 指定端口号

**客户端模式参数:**
- `--mode client` - 启动客户端模式  
- `--host <IP>` - 服务器IP地址
- `--port <端口>` - 服务器端口号

#### 图形界面模式

图形界面提供以下功能：

1. **模式选择** - 服务器或客户端模式
2. **网络配置** - IP地址和端口设置
3. **主机名设置** - 自定义设备标识
4. **自动保存配置** - 记住上次使用的设置
5. **实时日志** - 查看运行状态和错误信息
6. **系统托盘** - 最小化到托盘运行

### 架构说明

本项目采用标准的Server-Client架构：

- **SyncServer**: 作为中央枢纽，既参与剪贴板同步，又负责转发其他客户端的剪贴板内容
- **SyncClient**: 连接到服务器，发送本地剪贴板变化并接收其他设备的剪贴板内容
- **防回环机制**: 确保剪贴板内容不会回传给发送方，避免无限循环

### 开发者指南

#### 项目结构

```
src/
├── cli/           # 命令行接口
├── client/        # 客户端实现
├── server/        # 服务器实现
├── core/          # 核心组件
├── compat/        # 兼容性层
└── gui/           # 图形界面
```

#### 运行测试

```bash
# 运行所有测试
uv run python -m pytest tests/ -v

# 运行属性测试
uv run python -m pytest tests/test_anti_loop_properties.py -v

# 运行集成测试
uv run python -m pytest tests/test_integration.py -v
```

#### 贡献代码

1. Fork 本仓库
2. 创建功能分支: `git checkout -b feature/your-feature`
3. 提交更改: `git commit -am 'Add some feature'`
4. 推送分支: `git push origin feature/your-feature`
5. 创建 Pull Request

#### 代码规范

- 使用 Python 3.13+
- 遵循 PEP 8 代码风格
- 为新功能编写测试
- 更新相关文档

---

## English

A real-time clipboard synchronization tool across different operating systems using WebSocket. Built with a standard Server-Client architecture for stable and reliable cross-device clipboard sharing.

### Features

- 🚀 **Real-time Sync** - Millisecond-level clipboard synchronization via WebSocket
- 🔄 **Anti-loop Mechanism** - Smart prevention of infinite clipboard sync loops
- 🖥️ **Cross-platform** - Supports Windows and Linux operating systems
- 🔌 **Auto Reconnect** - Automatic client reconnection for service stability
- 🎛️ **Dual Interface** - Both command-line and graphical user interfaces
- ⚙️ **Flexible Config** - Customizable IP address, port, and hostname
- 📦 **Portable** - Can be packaged as standalone executables

### Quick Start

#### Install Dependencies

Using `uv` (recommended):
```bash
uv sync
```

Or using `pip`:
```bash
pip install websockets click pyperclip customtkinter pystray pillow
```

#### Basic Usage

1. **Start Server** (on main host):
   ```bash
   uv run python -m src.sync_clipboard --mode server --host 0.0.0.0 --port 8765
   ```

2. **Connect Client** (on other devices):
   ```bash
   uv run python -m src.sync_clipboard --mode client --host <SERVER_IP> --port 8765
   ```

3. **Use GUI**:
   ```bash
   uv run python -m src.sync_clipboard_gui
   ```

### Detailed Usage Guide

#### Command Line Mode

**Server Mode Parameters:**
- `--mode server` - Start in server mode
- `--host 0.0.0.0` - Listen on all network interfaces
- `--port 8765` - Specify port number

**Client Mode Parameters:**
- `--mode client` - Start in client mode
- `--host <IP>` - Server IP address
- `--port <PORT>` - Server port number

#### GUI Mode

The graphical interface provides:

1. **Mode Selection** - Server or client mode
2. **Network Configuration** - IP address and port settings
3. **Hostname Setting** - Custom device identifier
4. **Auto-save Config** - Remember last used settings
5. **Real-time Logs** - View running status and error messages
6. **System Tray** - Minimize to tray operation

### Architecture

This project uses a standard Server-Client architecture:

- **SyncServer**: Acts as central hub, participates in clipboard sync and forwards content from other clients
- **SyncClient**: Connects to server, sends local clipboard changes and receives content from other devices
- **Anti-loop Mechanism**: Ensures clipboard content doesn't loop back to sender, preventing infinite cycles

### Developer Guide

#### Project Structure

```
src/
├── cli/           # Command line interface
├── client/        # Client implementation
├── server/        # Server implementation
├── core/          # Core components
├── compat/        # Compatibility layer
└── gui/           # Graphical interface
```

#### Running Tests

```bash
# Run all tests
uv run python -m pytest tests/ -v

# Run property tests
uv run python -m pytest tests/test_anti_loop_properties.py -v

# Run integration tests
uv run python -m pytest tests/test_integration.py -v
```

#### Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -am 'Add some feature'`
4. Push branch: `git push origin feature/your-feature`
5. Create Pull Request

#### Code Standards

- Use Python 3.13+
- Follow PEP 8 style guide
- Write tests for new features
- Update relevant documentation

### Building Executables

#### Using PyInstaller

```bash
pyinstaller --onefile src/sync_clipboard.py
pyinstaller --onefile src/sync_clipboard_gui.py
```

Or use the provided spec files:

```bash
pyinstaller sync-clipboard.spec
pyinstaller sync-clipboard-gui.spec
```

#### Using Nix

For NixOS systems:

```bash
nix build
```

### Automated Releases

This project has GitHub Actions configured for automatic releases. When a tag in `vX.Y.Z` format is pushed:

1. Version number is extracted (removing `v` prefix)
2. Version is updated in `pyproject.toml`
3. Executables are built for Linux, Windows, and macOS
4. Packaged files are published to GitHub Release

#### Creating New Release

```bash
git tag v1.0.0
git push origin v1.0.0
```

### License

This project is open source. Please check the LICENSE file for details.

### Support

If you encounter any issues or have questions:

1. Check existing [Issues](../../issues)
2. Create a new issue with detailed description
3. Provide system information and error logs