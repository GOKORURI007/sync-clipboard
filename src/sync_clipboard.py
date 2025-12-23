#!/usr/bin/env python
# -*- coding:utf-8 -*-
import asyncio
import json
import platform
from typing import Set

import click
import websockets
from websockets import ClientConnection, ServerConnection


class ClipboardSync:
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
        self.clipboard_content = ""
        self.clients: Set[ClientConnection | ServerConnection] = set()
        self.websocket: ClientConnection | None = None
        self.server: websockets.Server | None = None
        self.is_syncing = False
        self.running = False
        self.log_callback = log_callback

        # 根据操作系统选择合适的剪贴板处理方式（仅客户端需要）
        if platform.system() in ["Windows", "Linux"]:
            try:
                import pyperclip
                self.clipboard_get = pyperclip.paste
                self.clipboard_set = pyperclip.copy
            except ImportError:
                self.log_callback("警告：需要安装 pyperclip 模块来访问剪贴板")
                self.clipboard_get = lambda: ""
                self.clipboard_set = lambda x: None
        else:
            self.log_callback(f"不支持的操作系统: {platform.system()}")
            self.clipboard_get = lambda: ""
            self.clipboard_set = lambda x: None

    async def start_server(self):
        """启动 WebSocket 服务器"""
        self.log_callback(f"正在启动服务器 {self.host}:{self.port}...")
        self.server = await websockets.serve(self.handle_client, self.host, self.port)
        self.log_callback(f"服务器已启动，等待客户端连接...")
        try:
            await self.server.wait_closed()
        except asyncio.CancelledError:
            await self.server.wait_closed()

    async def handle_client(self, websocket: ServerConnection):
        """处理客户端连接"""
        self.log_callback(f"新客户端已连接: {websocket.remote_address}")
        # 添加客户端到集合
        self.clients.add(websocket)

        try:
            async for message in websocket:
                data = json.loads(message)
                if data.get("type") == "clipboard_update":
                    content = data.get("content", "")
                    sender = data.get("sender", "")

                    # 只有当内容真正改变时才处理
                    if content.strip():
                        self.log_callback(
                            f"收到 {sender} 的新剪贴板内容: {content[:50]}{'...' if len(content) > 50 else ''}")

                        # 广播给其他客户端
                        await self.broadcast_clipboard_update(content, sender, websocket)
        except websockets.exceptions.ConnectionClosed:
            self.log_callback("客户端断开连接")
        finally:
            # 移除客户端
            self.clients.discard(websocket)

    async def broadcast_clipboard_update(self, content, sender, sender_socket=None):
        """广播剪贴板更新给所有客户端（除了发送者）"""
        if not self.clients:
            return

        message = json.dumps({
            "type": "clipboard_update",
            "content": content,
            "sender": sender
        })

        # 给所有客户端（除了发送者）发送更新
        disconnected_clients = set()
        for client in self.clients:
            if client != sender_socket:
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.add(client)

        # 清理已断开的客户端
        for client in disconnected_clients:
            self.clients.discard(client)

    async def start_client(self):
        """启动客户端并监听剪贴板变化"""
        uri = f"ws://{self.host}:{self.port}"
        retry_count = 0
        max_retries = 10

        while retry_count <= max_retries:
            try:
                self.log_callback(f"正在连接到服务器 {uri}...")
                websocket = await websockets.connect(
                    uri,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                )
                self.log_callback("已连接到服务器")
                self.websocket = websocket
                retry_count = 0  # 连接成功，重置重试计数

                # 创建两个并发任务：一个监听剪贴板变化，一个接收服务器消息
                await asyncio.gather(
                    self.monitor_clipboard(),
                    self.receive_messages()
                )
            except Exception as e:
                retry_count += 1
                if retry_count <= max_retries:
                    self.log_callback(f"连接错误: {e}")
                    self.log_callback(
                        f"3秒后尝试重新连接... (第 {retry_count}/{max_retries} 次)")
                    await asyncio.sleep(3)  # 3 秒后重试
                else:
                    self.log_callback(f"连接错误: {e}")
                    self.log_callback(f"已达到最大重试次数 ({max_retries})，程序退出")
                    raise

    async def monitor_clipboard(self):
        """监控剪贴板变化"""
        # 获取初始剪贴板内容
        self.clipboard_content = str(self.clipboard_get())

        # 持续监听剪贴板变化
        while self.running:
            await asyncio.sleep(0.5)  # 每 0.5 秒检查一次剪贴板
            current_content = str(self.clipboard_get())

            # 如果不是在同步过程中且内容发生了变化且不是空内容
            if not self.is_syncing and current_content != self.clipboard_content and current_content.strip():
                self.log_callback(
                    f"检测到本地剪贴板更新: {current_content[:50]}{'...' if len(current_content) > 50 else ''}")
                self.clipboard_content = current_content

                # 发送剪贴板内容到服务器
                try:
                    await self.websocket.send(json.dumps({
                        "type": "clipboard_update",
                        "content": current_content,
                        "sender": self.hostname
                    }))
                except websockets.exceptions.ConnectionClosed:
                    self.log_callback("与服务器连接已断开")
                    break

    async def receive_messages(self):
        """接收来自服务器的消息"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                if data.get("type") == "clipboard_update":
                    content = data.get("content", "")
                    sender = data.get("sender", "")

                    # 如果不是自己发送的内容，且不是空内容，则更新剪贴板
                    if content != self.clipboard_content and sender != self.hostname and content.strip():
                        self.log_callback(
                            f"收到 {sender} 的剪贴板更新: {content[:50]}{'...' if len(content) > 50 else ''}")
                        self.is_syncing = True
                        self.clipboard_set(content)
                        self.clipboard_content = content
                        self.is_syncing = False
        except websockets.exceptions.ConnectionClosed:
            self.log_callback("与服务器连接已断开")

    async def run_as_mix(self):
        """以混合模式运行，并处理优雅退出"""
        server_task = asyncio.create_task(self.start_server())
        client_task = asyncio.create_task(self.start_client())

        tasks = [server_task, client_task]

        try:
            # 使用 return_exceptions=False 确保一旦有一个崩溃，整体能响应
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            # 当接收到 Ctrl+C 或被手动取消时
            self.log_callback("\n正在接收退出信号，准备清理任务...")
        finally:
            self.running = False

            for t in tasks:
                if not t.done():
                    t.cancel()

            # 核心：给事件循环一点时间来运行清理代码（如 Server._close）
            # 使用 return_exceptions=True 避免在清理过程中抛出 CancelledError 导致中断
            await asyncio.gather(*tasks, return_exceptions=True)

            self.log_callback("所有任务已安全退出。")

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
        for task in asyncio.all_tasks(self.loop):
            task.cancel()

    def start_sync(self):
        """启动服务 (执行线程)"""
        self.running = True
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            # 运行直到 loop.stop() 被调用
            if self.mode == "server":
                self.loop.run_until_complete(self.start_server())
            elif self.mode == "client":
                self.loop.run_until_complete(self.start_client())
            elif self.mode == "mix":
                self.loop.run_until_complete(self.run_as_mix())
        except (KeyboardInterrupt, asyncio.CancelledError):
            raise
        finally:
            # 关键：在这里进行最后的收尾工作，此时 loop 已经处于 "stopped" 状态但未 "closed"
            self._cleanup_tasks_sync()  # 见下方
            self.loop.close()
            self.log_callback("服务已彻底停止。")

    def _cleanup_tasks_sync(self):
        """同步包装异步清理"""
        if not self.loop: return

        # 再次启动 loop 运行清理任务，完成后再次自动 stop
        pending = asyncio.all_tasks(self.loop)
        if pending:
            for task in pending:
                task.cancel()
            # 再次利用 run_until_complete 来消化掉取消信号和 websockets 的隐藏任务
            self.loop.run_until_complete(
                asyncio.gather(*pending, return_exceptions=True))


@click.command()
@click.option('--mode', '-m',
              type=click.Choice(['server', 'client', "mix"], case_sensitive=False),
              help='运行模式: server 或 client 或 mix')
@click.option('--host', '-h', default='127.0.0.1', help='服务器主机地址')
@click.option('--port', '-p', default=8765, type=int, help='服务器端口号')
def main(mode, host, port):
    """主函数"""
    if mode.lower() not in ['server', 'client', "mix"]:
        print("请指定运行模式: --mode server 或 --mode client 或 --mode mix")
        print("使用 --help 查看更多选项")
        return

    sync_clipboard = ClipboardSync(host, port, mode)
    try:
        sync_clipboard.start_sync()

    except KeyboardInterrupt:
        sync_clipboard.stop_sync()
        print("\n程序已退出")


if __name__ == "__main__":
    main()
