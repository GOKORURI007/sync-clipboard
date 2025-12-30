#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SyncServer implementation for sync-clipboard
"""
import asyncio
from typing import Dict, Optional

import websockets
from websockets import ServerConnection

from ..core.protocol import Message
from ..core.clipboard import ClipboardMonitor
from ..core.exceptions import ConnectionError, MessageFormatError
from ..core.logging_utils import get_logger


class SyncServer:
    """重构后的服务端类"""
    
    def __init__(self, host: str, port: int, hostname: str, log_callback=print):
        self.host = host
        self.port = port
        self.hostname = hostname
        self.clients: Dict[ServerConnection, str] = {}  # websocket -> client_id
        self.server: Optional[websockets.Server] = None
        self.log_callback = log_callback
        self.logger = get_logger("sync-server", log_callback)
        self.clipboard_monitor = ClipboardMonitor(self._on_local_clipboard_change)
        self.running = False
    
    async def start(self) -> None:
        """启动服务器"""
        self.running = True
        self.logger.info(f"正在启动服务器 {self.host}:{self.port}...")
        
        try:
            # 启动服务器和剪贴板监听
            server_task = asyncio.create_task(self._start_websocket_server())
            monitor_task = asyncio.create_task(self.clipboard_monitor.start_monitoring())
            
            await asyncio.gather(server_task, monitor_task)
        except asyncio.CancelledError:
            self.logger.info("服务器收到取消信号，正在关闭...")
            self.running = False
            if self.server:
                self.server.close()
                await self.server.wait_closed()
        except OSError as e:
            self.logger.error(f"网络错误，无法启动服务器: {e}", exc_info=True)
            raise ConnectionError(f"无法在 {self.host}:{self.port} 启动服务器: {e}")
        except Exception as e:
            self.logger.error(f"启动服务器时发生未知错误: {e}", exc_info=True)
            raise
    
    async def _start_websocket_server(self) -> None:
        """启动WebSocket服务器"""
        try:
            self.server = await websockets.serve(self.handle_client_connection, self.host, self.port)
            self.logger.info(f"服务器已启动，等待客户端连接...")
            await self.server.wait_closed()
        except OSError as e:
            self.logger.error(f"WebSocket服务器启动失败: {e}", exc_info=True)
            raise ConnectionError(f"WebSocket服务器启动失败: {e}")
        except Exception as e:
            self.logger.error(f"WebSocket服务器发生未知错误: {e}", exc_info=True)
            raise
    
    async def handle_client_connection(self, websocket: ServerConnection) -> None:
        """处理客户端连接"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.logger.info(f"新客户端已连接: {client_id}")
        
        try:
            # 等待客户端hello消息
            hello_message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            message = Message.from_json(hello_message)
            
            if message.type == "client_hello":
                client_hostname = message.sender_id
                self.add_client(websocket, client_hostname)
                
                # 处理后续消息
                async for raw_message in websocket:
                    try:
                        message = Message.from_json(raw_message)
                        if message.type == "clipboard_update":
                            await self._handle_clipboard_update(message, websocket)
                    except (ValueError, KeyError) as e:
                        self.logger.warning(f"收到无效消息格式，来自客户端 {client_id}: {e}")
                        continue
                        
        except asyncio.TimeoutError:
            self.logger.warning(f"客户端 {client_id} 连接超时，未收到hello消息")
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"客户端断开连接: {client_id}")
        except websockets.exceptions.WebSocketException as e:
            self.logger.error(f"WebSocket连接错误，客户端 {client_id}: {e}", exc_info=True)
        except (ValueError, KeyError) as e:
            self.logger.error(f"消息格式错误，来自客户端 {client_id}: {e}")
        except Exception as e:
            self.logger.error(f"处理客户端连接时出现未知错误 {client_id}: {e}", exc_info=True)
        finally:
            self.remove_client(websocket)
    
    async def _handle_clipboard_update(self, message: Message, sender_websocket: ServerConnection) -> None:
        """处理剪贴板更新消息"""
        content = message.content
        sender = message.sender_id
        
        if content.strip():
            self.logger.info(
                f"收到 {sender} 的新剪贴板内容: {content[:50]}{'...' if len(content) > 50 else ''}")
            
            # 广播给其他客户端（排除发送方）
            # 传递sender_websocket以便正确识别消息来源
            await self.broadcast_clipboard_update(content, sender_websocket)
    
    async def _on_local_clipboard_change(self, content: str) -> None:
        """本地剪贴板变化回调"""
        self.logger.info(
            f"检测到本地剪贴板更新: {content[:50]}{'...' if len(content) > 50 else ''}")
        
        # 广播给所有客户端
        await self.broadcast_clipboard_update(content)
    
    async def broadcast_clipboard_update(self, content: str, sender_websocket: Optional[ServerConnection] = None) -> None:
        """广播剪贴板更新给所有客户端（排除发送方）"""
        if not self.clients:
            return
        
        # 确定发送方的主机名，用于消息来源识别
        sender_hostname = self.hostname  # 默认是服务端自己
        if sender_websocket:
            sender_hostname = self.get_client_hostname(sender_websocket) or "unknown_client"
        
        message = Message(
            type="clipboard_update",
            sender_id=sender_hostname,
            content=content
        )
        
        # 给所有客户端（除了发送者）发送更新
        disconnected_clients = []
        for client_websocket, client_hostname in self.clients.items():
            # 排除发送方：既要排除websocket连接，也要排除相同主机名的客户端
            if (client_websocket != sender_websocket and 
                client_hostname != sender_hostname):
                try:
                    await client_websocket.send(message.to_json())
                    self.logger.info(f"已向客户端 {client_hostname} 广播剪贴板更新")
                except websockets.exceptions.ConnectionClosed:
                    self.logger.warning(f"客户端 {client_hostname} 连接已断开，将从列表中移除")
                    disconnected_clients.append(client_websocket)
                except websockets.exceptions.WebSocketException as e:
                    self.logger.error(f"向客户端 {client_hostname} 发送消息失败: {e}")
                    disconnected_clients.append(client_websocket)
                except Exception as e:
                    self.logger.error(f"向客户端 {client_hostname} 广播时发生未知错误: {e}", exc_info=True)
                    disconnected_clients.append(client_websocket)
        
        # 清理已断开的客户端
        for client in disconnected_clients:
            self.remove_client(client)
    
    def add_client(self, websocket: ServerConnection, client_id: str) -> None:
        """添加客户端连接"""
        self.clients[websocket] = client_id
        self.logger.info(f"客户端 {client_id} 已注册")
    
    def remove_client(self, websocket: ServerConnection) -> None:
        """移除客户端连接"""
        client_id = self.clients.pop(websocket, None)
        if client_id:
            self.logger.info(f"客户端 {client_id} 已断开")
    
    def get_client_hostname(self, websocket: ServerConnection) -> Optional[str]:
        """获取客户端主机名"""
        return self.clients.get(websocket)