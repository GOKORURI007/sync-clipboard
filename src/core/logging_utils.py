#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Logging utilities for sync-clipboard
"""

import logging
import sys
from typing import Callable, Optional


class SyncLogger:
    """同步剪贴板日志记录器"""

    def __init__(
        self, name: str = 'sync-clipboard', log_callback: Optional[Callable[[str], None]] = None
    ):
        self.logger = logging.getLogger(name)
        self.log_callback = log_callback
        self._setup_logger()

    def _setup_logger(self):
        """设置日志记录器"""
        if not self.logger.handlers:
            # 创建控制台处理器
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)

            # 创建格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)

            # 添加处理器到日志记录器
            self.logger.addHandler(console_handler)
            self.logger.setLevel(logging.INFO)

    def info(self, message: str):
        """记录信息日志"""
        self.logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def warning(self, message: str):
        """记录警告日志"""
        self.logger.warning(message)
        if self.log_callback:
            self.log_callback(f'警告: {message}')

    def error(self, message: str, exc_info: bool = False):
        """记录错误日志"""
        self.logger.error(message, exc_info=exc_info)
        if self.log_callback:
            self.log_callback(f'错误: {message}')

    def debug(self, message: str):
        """记录调试日志"""
        self.logger.debug(message)
        if self.log_callback:
            self.log_callback(f'调试: {message}')


def get_logger(
    name: str = 'sync-clipboard', log_callback: Optional[Callable[[str], None]] = None
) -> SyncLogger:
    """获取日志记录器实例"""
    return SyncLogger(name, log_callback)
