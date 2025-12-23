# sync-clipboard

通过WebSocket在不同操作系统之间同步剪贴板内容的工具。

## 功能特点

- 基于WebSocket实现实时剪贴板同步
- 支持Windows和Linux操作系统
- 可通过命令行参数配置IP地址和端口号
- 支持使用PyInstaller打包为可执行文件

## 安装依赖

首先安装项目所需依赖：

```bash
pip install websockets click pyperclip
```

如需打包为可执行文件，还需要安装 PyInstaller：

```bash
pip install pyinstaller
```

或者一次性安装所有依赖：

```bash
pip install websockets click pyperclip pyinstaller
```

## 使用方法

### 启动服务器模式

```bash
python main.py --mode server --host 0.0.0.0 --port 8765
```

### 启动客户端模式

```bash
python main.py --mode client --host SERVER_IP --port 8765
```

### 参数说明

- `--mode` 或 `-m`: 运行模式，可选 `server`（服务器）或 `client`（客户端）
- `--host` 或 `-h`: 服务器IP地址，默认为 `127.0.0.1`
- `--port` 或 `-p`: 端口号，默认为 `8765`

## 打包为可执行文件

### 使用PyInstaller

使用PyInstaller将程序打包为可执行文件：

```bash
pyinstaller --onefile main.py
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

## 使用示例

1. 在一台机器上启动服务器：
   ```
   python main.py --mode server --host 0.0.0.0 --port 8765
   ```

2. 在其他机器上连接到该服务器：
   ```
   python main.py --mode client --host SERVER_IP --port 8765
   ```

当任何一台机器的剪贴板发生变化时，其他机器的剪贴板也会自动同步更新。