import asyncio
import json
import platform
from typing import Set

import click
import websockets
from websockets import ClientConnection, ServerConnection


class ClipboardSync:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.clipboard_content = ""
        self.clients: Set[ClientConnection | ServerConnection] = set()
        self.websocket: ClientConnection | ServerConnection | None = None
        self.is_syncing = False  # 防止循环同步

        # 根据操作系统选择合适的剪贴板处理方式（仅客户端需要）
        if platform.system() == "Windows":
            try:
                import pyperclip
                self.clipboard_get = pyperclip.paste
                self.clipboard_set = pyperclip.copy
            except ImportError:
                print("警告：在 Windows 上需要安装 pyperclip 模块来访问剪贴板")
                self.clipboard_get = lambda: ""
                self.clipboard_set = lambda x: None
        elif platform.system() == "Linux":
            try:
                import pyperclip
                self.clipboard_get = pyperclip.paste
                self.clipboard_set = pyperclip.copy
            except ImportError:
                print("警告：在 Linux 上需要安装 pyperclip 模块来访问剪贴板")
                self.clipboard_get = lambda: ""
                self.clipboard_set = lambda x: None
        else:
            print(f"不支持的操作系统: {platform.system()}")
            self.clipboard_get = lambda: ""
            self.clipboard_set = lambda x: None

    async def start_server(self):
        """启动 WebSocket 服务器"""
        print(f"正在启动服务器 {self.host}:{self.port}...")
        async with websockets.serve(self.handle_client, self.host, self.port):
            print(f"服务器已启动，等待客户端连接...")
            await asyncio.Future()  # 运行直到被中断

    async def handle_client(self, websocket: ServerConnection):
        """处理客户端连接"""
        print(f"新客户端已连接: {websocket.remote_address}")
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
                        print(
                            f"收到 {sender} 的新剪贴板内容: {content[:50]}{'...' if len(content) > 50 else ''}")

                        # 广播给其他客户端
                        await self.broadcast_clipboard_update(content, sender, websocket)
        except websockets.exceptions.ConnectionClosed:
            print("客户端断开连接")
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
                print(f"正在连接到服务器 {uri}...")
                websocket = await websockets.connect(
                    uri,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                )
                print("已连接到服务器")
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
                    print(f"连接错误: {e}")
                    print(f"3秒后尝试重新连接... (第 {retry_count}/{max_retries} 次)")
                    await asyncio.sleep(3)  # 3 秒后重试
                else:
                    print(f"连接错误: {e}")
                    print(f"已达到最大重试次数 ({max_retries})，程序退出")
                    raise

    async def monitor_clipboard(self):
        """监控剪贴板变化"""
        # 获取初始剪贴板内容
        self.clipboard_content = str(self.clipboard_get())

        # 持续监听剪贴板变化
        while True:
            await asyncio.sleep(0.5)  # 每 0.5 秒检查一次剪贴板
            current_content = str(self.clipboard_get())

            # 如果不是在同步过程中且内容发生了变化且不是空内容
            if not self.is_syncing and current_content != self.clipboard_content and current_content.strip():
                print(
                    f"检测到本地剪贴板更新: {current_content[:50]}{'...' if len(current_content) > 50 else ''}")
                self.clipboard_content = current_content

                # 发送剪贴板内容到服务器
                try:
                    await self.websocket.send(json.dumps({
                        "type": "clipboard_update",
                        "content": current_content,
                        "sender": "client"
                    }))
                except websockets.exceptions.ConnectionClosed:
                    print("与服务器连接已断开")
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
                    if content != self.clipboard_content and content.strip():
                        print(
                            f"收到 {sender} 的剪贴板更新: {content[:50]}{'...' if len(content) > 50 else ''}")
                        self.is_syncing = True
                        self.clipboard_set(content)
                        self.clipboard_content = content
                        self.is_syncing = False
        except websockets.exceptions.ConnectionClosed:
            print("与服务器连接已断开")

    async def run_as_server(self):
        """作为服务器运行"""
        await self.start_server()

    async def run_as_client(self):
        """作为客户端运行"""
        await self.start_client()

    async def run_as_mix(self):
        """作为客户端运行"""
        await asyncio.gather(
            self.start_server(),
            self.start_client()
        )


@click.command()
@click.option('--mode', '-m',
              type=click.Choice(['server', 'client', "mix"], case_sensitive=False),
              help='运行模式: server 或 client 或 mix')
@click.option('--host', '-h', default='127.0.0.1', help='服务器主机地址')
@click.option('--port', '-p', default=8765, type=int, help='服务器端口号')
def main(mode, host, port):
    """主函数"""

    sync_clipboard = ClipboardSync(host, port)

    try:
        match mode.lower():
            case 'server':
                print("以服务器模式运行...")
                asyncio.run(sync_clipboard.run_as_server())
            case 'mix':
                print("以混合模式运行...")
                asyncio.run(sync_clipboard.run_as_mix())
            case 'client':
                print("以客户端模式运行...")
                asyncio.run(sync_clipboard.run_as_client())

            case _:
                print("请指定运行模式: --mode server 或 --mode client 或 --mode mix")
                print("使用 --help 查看更多选项")
                return

    except KeyboardInterrupt:
        print("\n程序已退出")


if __name__ == "__main__":
    main()
