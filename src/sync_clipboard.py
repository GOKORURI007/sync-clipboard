#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Sync Clipboard - A cross-platform clipboard synchronization tool
Main entry point that imports from modular components
"""

# Import all components for backward compatibility
from .core.version import __version__
from .core.protocol import Message
from .core.config import Config
from .core.clipboard import ClipboardMonitor
from .server.sync_server import SyncServer
from .client.sync_client import SyncClient
from .compat.clipboard_sync import ClipboardSync
from .cli.main import main

# Export all public components
__all__ = [
    '__version__',
    'Message',
    'Config', 
    'ClipboardMonitor',
    'SyncServer',
    'SyncClient',
    'ClipboardSync',
    'main'
]

if __name__ == "__main__":
    main()
