#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Exception classes for sync-clipboard
"""


class SyncClipboardError(Exception):
    """基础异常类"""
    pass


class ClipboardConnectionError(SyncClipboardError):
    """连接相关错误"""
    pass


class ClipboardAccessError(SyncClipboardError):
    """剪贴板访问错误"""
    pass


class MessageFormatError(SyncClipboardError):
    """消息格式错误"""
    pass


class ConfigurationError(SyncClipboardError):
    """配置错误"""
    pass
