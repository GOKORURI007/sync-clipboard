#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Configuration management for sync-clipboard
"""

import platform
from dataclasses import dataclass


@dataclass
class Config:
    """配置类"""

    mode: str = 'client'  # "server" or "client"
    host: str = '127.0.0.1'
    port: int = 8765
    hostname: str = ''
    auto_reconnect: bool = True
    max_retries: int = 10

    def __post_init__(self):
        if not self.hostname:
            self.hostname = platform.node()
