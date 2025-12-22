import asyncio
import json
import sys
import click
import websockets
import platform
from typing import Optional


class ClipboardSync:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.clipboard_content = ""
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        
        # 根据操作系统选择合适的剪贴板处理方式
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

    async def handle_client(self, websocket, path):
        """处理客户端连接"""
        print(f"新客户端已连接: {websocket.remote_address}")
        self.websocket = websocket
        
        try:
            async for message in websocket:
                data = json.loads(message)
                if data.get("type") == "clipboard_update":
                    content = data.get("content", "")
                    if content != self.clipboard_content:
                        print(f"收到新的剪贴板内容: {content[:50]}...")
                        self.clipboard_set(content)
                        self.clipboard_content = content
        except websockets.exceptions.ConnectionClosed:
            print("客户端断开连接")
        finally:
            if self.websocket == websocket:
                self.websocket = None

    async def start_client(self):
        """启动客户端并监听剪贴板变化"""
        uri = f"ws://{self.host}:{self.port}"
        print(f"正在连接到服务器 {uri}...")
        
        try:
            async with websockets.connect(uri) as websocket:
                print("已连接到服务器")
                self.websocket = websocket
                
                # 获取初始剪贴板内容
                self.clipboard_content = self.clipboard_get()
                
                # 持续监听剪贴板变化
                while True:
                    await asyncio.sleep(0.5)  # 每0.5秒检查一次剪贴板
                    current_content = self.clipboard_get()
                    
                    if current_content != self.clipboard_content:
                        print(f"检测到剪贴板更新: {current_content[:50]}...")
                        self.clipboard_content = current_content
                        
                        # 发送剪贴板内容到服务器
                        await websocket.send(json.dumps({
                            "type": "clipboard_update",
                            "content": current_content
                        }))
                        
        except Exception as e:
            print(f"连接错误: {e}")

    async def run_as_server(self):
        """作为服务器运行"""
        await self.start_server()

    async def run_as_client(self):
        """作为客户端运行"""
        await self.start_client()


@click.command()
@click.option('--mode', '-m', type=click.Choice(['server', 'client'], case_sensitive=False),
              help='运行模式: server 或 client')
@click.option('--host', '-h', default='127.0.0.1', help='服务器主机地址')
@click.option('--port', '-p', default=8765, type=int, help='服务器端口号')
def main(mode, host, port):
    """主函数"""
    if mode is None:
        print("请指定运行模式: --mode server 或 --mode client")
        print("使用 --help 查看更多选项")
        return

    clipboard_sync = ClipboardSync(host, port)
    
    try:
        if mode.lower() == 'server':
            print("以服务器模式运行...")
            asyncio.run(clipboard_sync.run_as_server())
        else:
            print("以客户端模式运行...")
            asyncio.run(clipboard_sync.run_as_client())
    except KeyboardInterrupt:
        print("\\n程序已退出")


if __name__ == "__main__":
    main()