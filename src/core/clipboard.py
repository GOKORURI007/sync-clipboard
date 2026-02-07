#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Clipboard monitoring and management for sync-clipboard
"""

import asyncio
import platform
from typing import Awaitable, Callable

from .exceptions import ClipboardAccessError
from .logging_utils import get_logger


class ClipboardMonitor:
    """剪贴板监听器"""

    def __init__(self, callback: Callable[[str], Awaitable[None]]):
        self.callback = callback
        self.cached_content = ''
        self.is_syncing = False
        self.logger = get_logger('clipboard-monitor')
        self._setup_clipboard_backend()

    def _setup_clipboard_backend(self):
        """设置剪贴板后端"""
        if platform.system() in ['Windows', 'Linux']:
            try:
                import pyperclip

                self.clipboard_get = pyperclip.paste
                self.clipboard_set = pyperclip.copy
                self.logger.info(f'已初始化剪贴板后端，支持平台: {platform.system()}')
            except ImportError as e:
                self.logger.error(f'无法导入 pyperclip 模块: {e}')
                self.logger.warning('剪贴板功能将被禁用，请安装 pyperclip 模块')
                self.clipboard_get = lambda: ''
                self.clipboard_set = lambda x: None
        else:
            self.logger.error(f'不支持的操作系统: {platform.system()}')
            self.clipboard_get = lambda: ''
            self.clipboard_set = lambda x: None

    async def start_monitoring(self) -> None:
        """开始监听剪贴板变化"""
        try:
            self.cached_content = str(self._safe_clipboard_get())
        except ClipboardAccessError as e:
            self.logger.warning(f'初始化剪贴板内容失败: {e}')
            self.cached_content = ''

        self.logger.info('开始监听剪贴板变化')

        while True:
            await asyncio.sleep(0.5)  # 每 0.5 秒检查一次剪贴板

            # 如果正在同步过程中，跳过检查以防止回环
            if self.is_syncing:
                continue

            try:
                current_content = str(self._safe_clipboard_get())

                # 内容变化检测：只有在内容确实改变且不是空内容时才触发同步
                if self._is_content_changed(current_content):
                    self.cached_content = current_content
                    await self.callback(current_content)

            except ClipboardAccessError as e:
                self.logger.warning(f'读取剪贴板失败，继续监听: {e}')
                # 继续运行，不中断监听
                continue
            except Exception as e:
                self.logger.error(f'监听剪贴板时发生未知错误: {e}', exc_info=True)
                # 继续运行，不中断监听
                continue

    async def update_clipboard(self, content: str) -> None:
        """更新本地剪贴板（防回环）"""
        if content != self.cached_content and content.strip():
            # 设置同步状态标志，防止触发新的同步循环
            self.is_syncing = True
            try:
                self._safe_clipboard_set(content)
                self.cached_content = content
                self.logger.debug(
                    f'已更新剪贴板内容: {content[:50]}{"..." if len(content) > 50 else ""}'
                )
                # 短暂等待确保剪贴板更新完成
                await asyncio.sleep(0.1)
            except ClipboardAccessError as e:
                self.logger.warning(f'更新剪贴板失败，但程序继续运行: {e}')
                # 不抛出异常，让程序继续运行
            except Exception as e:
                self.logger.error(f'更新剪贴板时发生未知错误: {e}', exc_info=True)
                # 不抛出异常，让程序继续运行
            finally:
                # 确保同步标志被重置，即使出现异常
                self.is_syncing = False

    def _safe_clipboard_get(self) -> str:
        """安全地获取剪贴板内容"""
        try:
            return self.clipboard_get()
        except Exception as e:
            self.logger.warning(f'访问剪贴板失败: {e}')
            raise ClipboardAccessError(f'无法读取剪贴板内容: {e}')

    def _safe_clipboard_set(self, content: str) -> None:
        """安全地设置剪贴板内容"""
        try:
            self.clipboard_set(content)
        except Exception as e:
            self.logger.warning(f'设置剪贴板失败: {e}')
            raise ClipboardAccessError(f'无法设置剪贴板内容: {e}')

    def _is_content_changed(self, new_content: str) -> bool:
        """检测内容是否真正发生变化（去除空白字符影响）"""
        # 标准化内容：去除首尾空白，统一换行符
        normalized_current = self.cached_content.strip().replace('\r\n', '\n').replace('\r', '\n')
        normalized_new = new_content.strip().replace('\r\n', '\n').replace('\r', '\n')

        return normalized_current != normalized_new and normalized_new
