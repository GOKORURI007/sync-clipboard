# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['src/sync_clipboard_cli.py'],  # 入口脚本
    pathex=[],  # 额外模块搜索路径
    binaries=[],
    datas=[('pyproject.toml', '.')],  # 把包内数据文件打进去
    hiddenimports=[],  # 无隐式 import 可留空
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name='sync-clipboard',  # 输出文件名（Win 自动加 .exe）
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # CLI 需要控制台
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)