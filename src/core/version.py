#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version management for sync-clipboard
"""
import os
import sys
import tomllib
from pathlib import Path


def get_version():
    """获取应用程序版本"""
    # 1. 优先尝试 Nix 注入的环境变量 (适用于 nix build)
    nix_version = os.getenv("APP_VERSION")
    if nix_version:
        return nix_version

    # 2. 尝试从 PyInstaller 打包后的路径读取
    # PyInstaller 运行时会创建 _MEIPASS 临时目录
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent.parent.parent

    toml_path = base_path / "pyproject.toml"

    if toml_path.exists():
        try:
            with open(toml_path, "rb") as f:
                return tomllib.load(f).get("project", {}).get("version", "0.1.0")
        except FileNotFoundError as e:
            print(e)

    return "unknown"  # 最终保底版本


__version__ = get_version()