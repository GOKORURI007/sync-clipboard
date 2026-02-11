# Sync Clipboard | Cross-device Clipboard Synchronization Tool

![GitHub License](https://img.shields.io/github/license/GOKORURI007/sync-clipboard?link=https%3A%2F%2Fgithub.com%2FGOKORURI007%2Fsync-clipboard%2Fblob%2Fmaster%2FLICENSE)
![Python Version](https://img.shields.io/badge/python-3.13%2B-blue)

[English](./README.md) | [简体中文](./docs/README-zhCN.md)

Sync Clipboard is a cross-platform real-time clipboard synchronization tool based on WebSocket
technology, featuring a standard Server-Client architecture design. It aims to solve the unstable
clipboard functionality issues found in keyboard-mouse sharing software
like [Deskflow](https://github.com/deskflow/deskflow).

## 📋 Feature Support Matrix

| Feature Category      | Status        | Description                                                            |
|-----------------------|---------------|------------------------------------------------------------------------|
| Text Synchronization  | ✅ Supported   | Supports plain text and rich text content                              |
| Image Synchronization | ⏳ Not Planned | Depends on [pyperclip](https://github.com/asweigart/pyperclip) support |
| File Synchronization  | ⏳ Not Planned | Depends on [pyperclip](https://github.com/asweigart/pyperclip) support |
| Windows               | ✅ Supported   | Full feature support                                                   |
| Linux/X11             | ✅ Supported   | Through X11 clipboard API                                              |
| Linux/Wayland         | ✅ Supported   | Through wl-clipboard tool                                              |
| macOS                 | ⏳ Untested    | Theoretically supported, testing feedback welcome                      |

## 🚀 Quick Start

### 📦 Installation Methods

#### 🔧 Distribution Installation (Windows & Linux & MacOS)

Download the pre-compiled version for your platform from
the [GitHub Release](https://github.com/GOKORURI007/sync-clipboard/releases) page.

#### 💻 Scoop Package Manager (Windows Recommended)

```powershell
# 1. Add custom bucket
scoop bucket add ruri-scoop "https://github.com/gokoruri007/ruri-scoop"

# 2. Install GUI version (recommended)
scoop install ruri-scoop/sync-clipboard-gui

# 3. Install CLI version (optional)
scoop install ruri-scoop/sync-clipboard-cli
```

#### 🛠️ Build from Source (Windows & Linux & MacOS)

```bash
# 1. Clone the project
git clone https://github.com/GOKORURI007/sync-clipboard.git
cd sync-clipboard

# 2. Install dependencies (recommended using uv)
uv sync

# 3. Run module directly
uv run python -m src.sync_clipboard_cli --mode server --host 0.0.0.0 --port 8765
# Or start GUI
uv run python -m src.sync_clipboard_gui

# 4. Package as executable
uv run pyinstaller sync-clipboard-cli.spec
uv run pyinstaller sync-clipboard-gui.spec
```

### 🧊 Nix/Flake (NixOS Recommended)

Add configuration to your `flake.nix`:

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
            wl-clipboard  # Wayland support
            xclip         # X11 support
          ];
        }
      ];
    };
  };
}
```

Run via systemd service:

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

## 🎯 Usage Guide

### 🖥️ Command Line Mode

**Server Startup:**

```bash
# Listen on all network interfaces
sync-clipboard --mode server --host 0.0.0.0 --port 8765

# Listen on localhost only
sync-clipboard --mode server --host 127.0.0.1 --port 8765
```

**Client Connection:**

```bash
# Connect to remote server
sync-clipboard --mode client --host 192.168.1.100 --port 8765

# Use custom hostname identifier
sync-clipboard --mode client --host server.local --port 8765 --hostname my-laptop
```

**Command Line Commands:**

### 🖱️ Graphical Interface Mode

Launch the GUI:

```bash
sync-clipboard-gui
```

### ⚙️ Advanced Configuration

Configuration file location:

- **Windows**: `%APPDATA%/sync-clipboard/config.json`
- **Linux/macOS**: `~/.config/sync-clipboard/config.json`

Example configuration:

```json
{
    "mode": "client",
    "host": "192.168.1.100",
    "port": 8765,
    "hostname": "my-workstation",
    "minimize_on_close": true
}
```

## 🏗️ Technical Architecture

### 📊 System Architecture

```
┌─────────────────┐    WebSocket    ┌─────────────────┐
│   SyncServer    │◄───────────────►│   SyncClient    │
│  (Central Hub)  │                 │   (Terminal Node)│
└─────────────────┘                 └─────────────────┘
         │                                   │
         ▼                                   ▼
┌─────────────────┐                 ┌─────────────────┐
│ ClipboardMonitor│                 │ ClipboardMonitor│
│   (Local Listener)│               │   (Local Listener)│
└─────────────────┘                 └─────────────────┘
```

### 📁 Project Structure

```
sync-clipboard/
├── src/                             # Source code directory
│   ├── core/                        # Core modules
│   │   ├── clipboard.py             # Clipboard operation core
│   │   ├── protocol.py              # Communication protocol definition
│   │   ├── config.py                # Configuration management
│   │   └── exceptions.py            # Exception definitions
│   ├── server/                      # Server implementation
│   │   └── sync_server.py           # WebSocket server
│   ├── client/                      # Client implementation
│   │   └── sync_client.py           # WebSocket client
│   ├── compat/                      # Compatibility layer
│   ├── sync_clipboard_cli.py        # Command line interface
│   └── sync_clipboard_gui.py        # Graphical interface
├── tests/                           # Test suite
│   ├── test_integration.py          # Integration tests
│   └── test_anti_loop_properties.py # Anti-loop property tests
├── scripts/                         # Development helper scripts
│   ├── format.py                    # Code formatting
│   ├── release.py                   # Version release
│   └── test_all.py                  # Test runner
├── assets/                          # Resource files
├── docs/                            # Documentation
├── pyproject.toml                   # Project configuration
└── README.md                        # English documentation
```

## 👨‍💻 Development Guide

### 🛠️ Development Environment Setup

```bash
# 1. Clone the project
git clone https://github.com/GOKORURI007/sync-clipboard.git
cd sync-clipboard

# 2. Install dependency management tool
# Recommended using uv (https://github.com/astral-sh/uv)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Initialize development environment
uv sync

# 4. Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

### 🧪 Running Tests

```bash
uv run python scripts/test_all.py
```

### 🎨 Code Quality

```bash
# Code formatting
uv run python scripts/format.py
```

### 🚀 Building Releases

```bash
# Create new version
uv run python scripts/release.py

# Package executable
uv run pyinstaller sync-clipboard-cli.spec
uv run pyinstaller sync-clipboard-gui.spec
```

## 🤝 Contribution Guidelines

We welcome contributions of any form!

### 📝 Contribution Process

1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Format code: `uv run python scripts/format.py`
4. Commit changes: `git commit -am 'Add some feature'`
5. Push branch: `git push origin feature/your-feature`
6. Create Pull Request

### 🎯 Development Standards

- Follow [PEP 8](https://peps.python.org/pep-0008/) coding style
- Update relevant documentation and comments
- Use type hints to enhance code readability
- Maintain clear and descriptive commit messages

### 🐛 Reporting Issues

Please report issues in [Issues](https://github.com/GOKORURI007/sync-clipboard/issues), including:

- Operating system and version used
- Sync Clipboard version
- Detailed error description and reproduction steps
- Relevant log output

## 📄 License

This project is licensed under the MIT License. See
the [LICENSE](https://github.com/GOKORURI007/sync-clipboard/blob/master/LICENSE) file for details.

## 🙏 Acknowledgments

Thanks to the following open-source projects for their support:

- [websockets](https://github.com/aaugustin/websockets) - WebSocket implementation
- [pyperclip](https://github.com/asweigart/pyperclip) - Cross-platform clipboard operations
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern GUI framework
- [pystray](https://github.com/moses-palmer/pystray) - System tray support

## 📞 Contact

- Project Homepage: [GitHub Repository](https://github.com/GOKORURI007/sync-clipboard)
- Issue Tracker: [Issue Tracker](https://github.com/GOKORURI007/sync-clipboard/issues)
