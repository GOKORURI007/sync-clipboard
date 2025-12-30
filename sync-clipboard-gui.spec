# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['src/sync_clipboard_gui.py'],  # 入口脚本
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
    name='sync-clipboard-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
