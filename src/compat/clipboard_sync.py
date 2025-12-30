#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Compatibility wrapper for sync-clipboard
Maintains backward compatibility with existing code
"""
import asyncio
import platform

from ..server.sync_server import SyncServer
from ..client.sync_client import SyncClient


class ClipboardSync:
    """兼容性包装类，保持向后兼容"""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        mode: str = "client",
        hostname: str = "",
        log_callback=print
    ):
        self.loop: asyncio.AbstractEventLoop | None = None
        self.hostname = hostname or platform.node()
        self.host = host
        self.port = port
        self.mode = mode
        self.running = False
        self.log_callback = log_callback
        
        # 验证模式
        if mode not in ["server", "client"]:
            raise ValueError(f"不支持的模式: {mode}。只支持 'server' 或 'client'")
        
        # 创建对应的实例
        if mode == "server":
            self.instance = SyncServer(host, port, self.hostname, log_callback)
        else:  # client
            self.instance = SyncClient(host, port, self.hostname, log_callback=log_callback)

    def stop_sync(self):
        """停止服务 (由 GUI 或其他线程调用)"""
        if not self.running:
            return

        self.running = False
        if self.loop and self.loop.is_running():
            # 跨线程安全地在 loop 中执行取消逻辑
            self.loop.call_soon_threadsafe(self._cancel_all_tasks)

    def _cancel_all_tasks(self):
        """在 loop 线程内执行的具体取消逻辑"""
        current = asyncio.current_task(self.loop)
        for task in asyncio.all_tasks(self.loop):
            if task is not current:
                task.cancel()

    def start_sync(self):
        """启动服务 (执行线程)"""
        self.running = True
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            # 运行直到 loop.stop() 被调用
            if self.mode == "server":
                self.loop.run_until_complete(self.instance.start())
            elif self.mode == "client":
                self.loop.run_until_complete(self.instance.start())
        except (KeyboardInterrupt, asyncio.CancelledError):
            raise
        finally:
            # 关键：在这里进行最后的收尾工作，此时 loop 已经处于 "stopped" 状态但未 "closed"
            self._cleanup_tasks_sync()
            self.loop.close()
            self.log_callback("服务已彻底停止。")

    def _cleanup_tasks_sync(self):
        """同步包装异步清理"""
        if not self.loop:
            return

        # 再次启动 loop 运行清理任务，完成后再次自动 stop
        pending = asyncio.all_tasks(self.loop)
        if pending:
            for task in pending:
                task.cancel()
            # 再次利用 run_until_complete 来消化掉取消信号和 websockets 的隐藏任务
            self.loop.run_until_complete(
                asyncio.gather(*pending, return_exceptions=True))