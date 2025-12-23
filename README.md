# sync-clipboard

通过WebSocket在不同操作系统之间同步剪贴板内容的工具。

## 功能特点

- 基于WebSocket实现实时剪贴板同步
- 支持Windows和Linux操作系统
- 可通过命令行参数配置IP地址和端口号
- 支持使用PyInstaller打包为可执行文件
- 提供图形用户界面（GUI）版本

## 安装依赖

首先安装项目所需依赖：

```bash
pip install websockets click pyperclip customtkinter pystray pillow
```

如需打包为可执行文件，还需要安装 PyInstaller：

```bash
pip install pyinstaller
```

或者一次性安装所有依赖：

```bash
pip install websockets click pyperclip customtkinter pystray pillow pyinstaller
```

## 使用方法

### 命令行版本

#### 启动服务器模式

```bash
python -m src.sync_clipboard --mode server --host 0.0.0.0 --port 8765
```

### 启动客户端模式

```bash
python -m src.sync_clipboard --mode client --host SERVER_IP --port 8765
```

### 参数说明

- `--mode` 或 `-m`: 运行模式，可选 `server`（服务器）或 `client`（客户端）
- `--host` 或 `-h`: 服务器IP地址，默认为 `127.0.0.1`
- `--port` 或 `-p`: 端口号，默认为 `8765`

### 图形界面版本

从 v0.2.0 版本开始，项目提供图形用户界面版本，支持以下功能：

1. **设置运行模式** - 通过单选按钮可以选择服务器(server)、客户端(client)或混合(mix)模式
2. **修改IP和端口** - 提供了输入框用于修改主机地址和端口号
3. **修改主机名** - 可以自定义当前设备的主机名
4. **保存配置** - 应用会自动保存上一次的配置
5. **控制按钮** - 提供了开始运行、停止运行和完全退出的按钮
6. **日志窗口** - 实时显示运行日志信息
7. **系统托盘** - 应用可以最小化到托盘，并通过托盘重新打开主界面或完全退出

启动图形界面版本：

```bash
python -m src.sync_clipboard_gui
```

或使用命令：

```bash
sync-clipboard-gui
```

## 打包为可执行文件

### 使用PyInstaller

使用PyInstaller将程序打包为可执行文件：

```bash
pyinstaller --onefile src/sync_clipboard.py
pyinstaller --onefile src/sync_clipboard_gui.py
```

或者使用项目提供的spec文件：

```bash
pyinstaller sync-clipboard.spec
```

打包后的可执行文件位于 `dist/` 目录中。

### 使用Nix

如果在NixOS系统上，也可以使用Nix来构建：

```bash
nix build
```

构建后的可执行文件可通过 `./result/bin/sync-clipboard` 访问。

## 自动发布

本项目配置了GitHub Actions自动发布功能，当给某个commit打上`vX.Y.Z`格式的tag时，会自动执行以下操作：

1. 从tag中提取版本号（去掉`v`前缀）
2. 将提取的版本号更新到[pyproject.toml](./pyproject.toml)文件中
3. 使用PyInstaller为Linux、Windows和macOS三个平台打包可执行文件
4. 将打包好的可执行文件发布到GitHub Release中

### 创建新版本

```bash
# 为当前commit打上版本tag
git tag vX.Y.Z
git push origin vX.Y.Z
```

例如：

```bash
git tag v1.0.0
git push origin v1.0.0
```

## 使用示例

1. 在一台机器上启动服务器：
   ```
   python -m src.sync_clipboard --mode server --host 0.0.0.0 --port 8765
   ```

2. 在其他机器上连接到该服务器：
   ```
   python -m src.sync_clipboard --mode client --host SERVER_IP --port 8765
   ```

当任何一台机器的剪贴板发生变化时，其他机器的剪贴板也会自动同步更新。