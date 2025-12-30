#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SyncClient implementation for sync-clipboard
"""
import asyncio
from typing import Optional

import websockets
from websockets import ClientConnection

from ..core.clipboard import ClipboardMonitor
from ..core.exceptions import ClipboardConnectionError
from ..core.logging_utils import get_logger
from ..core.protocol import Message


class SyncClient:
    """重构后的客户端类"""
    
    def __init__(self, server_host: str, server_port: int, hostname: str, 
                 auto_reconnect: bool = True, max_retries: int = 10, log_callback=print):
        self.server_host = server_host
        self.server_port = server_port
        self.hostname = hostname
        self.websocket: Optional[ClientConnection] = None
        self.clipboard_monitor = ClipboardMonitor(self._on_local_clipboard_change)
        self.auto_reconnect_enabled = auto_reconnect
        self.max_retries = max_retries
        self.retry_count = 0
        self.log_callback = log_callback
        self.logger = get_logger("sync-client", log_callback)
        self.running = False
    
    async def start(self) -> None:
        """启动客户端"""
        self.running = True
        
        while self.running and self.retry_count <= self.max_retries:
            try:
                await self.connect()
                self.retry_count = 0  # 连接成功，重置重试计数
                
                # 启动剪贴板监听和消息接收
                monitor_task = asyncio.create_task(self.clipboard_monitor.start_monitoring())
                receive_task = asyncio.create_task(self._receive_messages())
                
                await asyncio.gather(monitor_task, receive_task)

            except ClipboardConnectionError as e:
                self.logger.error(f"连接错误: {e}")
                if self.auto_reconnect_enabled and self.running:
                    await self.attempt_reconnect()
                else:
                    break
            except websockets.exceptions.WebSocketException as e:
                self.logger.error(f"WebSocket错误: {e}", exc_info=True)
                if self.auto_reconnect_enabled and self.running:
                    await self.attempt_reconnect()
                else:
                    break
            except OSError as e:
                self.logger.error(f"网络错误: {e}", exc_info=True)
                if self.auto_reconnect_enabled and self.running:
                    await self.attempt_reconnect()
                else:
                    break
            except Exception as e:
                self.logger.error(f"客户端发生未知错误: {e}", exc_info=True)
                if self.auto_reconnect_enabled and self.running:
                    await self.attempt_reconnect()
                else:
                    break
    
    async def connect(self) -> None:
        """连接到服务器"""
        uri = f"ws://{self.server_host}:{self.server_port}"
        self.logger.info(f"正在连接到服务器 {uri}...")
        
        try:
            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    uri,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                ),
                timeout=30.0
            )
            
            # 发送hello消息
            hello_message = Message(
                type="client_hello",
                sender_id=self.hostname
            )
            await self.websocket.send(hello_message.to_json())
            
            self.logger.info("已连接到服务器")
            
        except asyncio.TimeoutError:
            self.logger.error(f"连接服务器超时: {uri}")
            raise ClipboardConnectionError(f"连接服务器超时: {uri}")
        except OSError as e:
            self.logger.error(f"网络连接失败: {e}")
            raise ClipboardConnectionError(f"网络连接失败: {e}")
        except websockets.exceptions.WebSocketException as e:
            self.logger.error(f"WebSocket连接失败: {e}")
            raise ClipboardConnectionError(f"WebSocket连接失败: {e}")
        except Exception as e:
            self.logger.error(f"连接时发生未知错误: {e}", exc_info=True)
            raise ClipboardConnectionError(f"连接时发生未知错误: {e}")
    
    async def _on_local_clipboard_change(self, content: str) -> None:
        """本地剪贴板变化回调"""
        self.logger.info(
            f"检测到本地剪贴板更新: {content[:50]}{'...' if len(content) > 50 else ''}")
        
        await self.send_clipboard_update(content)
    
    async def send_clipboard_update(self, content: str) -> None:
        """发送剪贴板更新到服务器"""
        if self.websocket:
            message = Message(
                type="clipboard_update",
                sender_id=self.hostname,
                content=content
            )
            try:
                await self.websocket.send(message.to_json())
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("与服务器连接已断开")
                raise ClipboardConnectionError("与服务器连接已断开")
            except websockets.exceptions.WebSocketException as e:
                self.logger.error(f"发送消息失败: {e}")
                raise ClipboardConnectionError(f"发送消息失败: {e}")
            except Exception as e:
                self.logger.error(f"发送剪贴板更新时发生未知错误: {e}", exc_info=True)
                raise
    
    async def _receive_messages(self) -> None:
        """接收来自服务器的消息"""
        try:
            async for raw_message in self.websocket:
                try:
                    message = Message.from_json(raw_message)
                    await self.handle_server_message(message)
                except (ValueError, KeyError) as e:
                    self.logger.warning(f"收到无效消息格式: {e}")
                    continue
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("与服务器连接已断开")
            raise ClipboardConnectionError("与服务器连接已断开")
        except websockets.exceptions.WebSocketException as e:
            self.logger.error(f"接收消息时发生WebSocket错误: {e}")
            raise ClipboardConnectionError(f"接收消息时发生WebSocket错误: {e}")
        except Exception as e:
            self.logger.error(f"接收消息时发生未知错误: {e}", exc_info=True)
            raise
    
    async def handle_server_message(self, message: Message) -> None:
        """处理来自服务器的消息"""
        if message.type == "clipboard_update":
            content = message.content
            sender = message.sender_id
            
            # 防回环：忽略自己发送的消息
            if sender == self.hostname:
                self.logger.debug(f"忽略自己发送的消息: {content[:50]}{'...' if len(content) > 50 else ''}")
                return
            
            # 如果不是自己发送的内容，且不是空内容，则更新剪贴板
            if content.strip():
                self.logger.info(
                    f"收到 {sender} 的剪贴板更新: {content[:50]}{'...' if len(content) > 50 else ''}")
                await self.clipboard_monitor.update_clipboard(content)
    
    async def attempt_reconnect(self) -> bool:
        """尝试重连，使用指数退避策略"""
        if not self.auto_reconnect_enabled or self.retry_count >= self.max_retries:
            self.logger.error(f"已达到最大重连次数 {self.max_retries}，停止重连")
            return False
        
        self.retry_count += 1
        wait_time = min(2 ** self.retry_count, 60)  # 指数退避，最大60秒
        
        self.logger.info(f"连接断开，{wait_time}秒后尝试重新连接... (第 {self.retry_count}/{self.max_retries} 次)")
        await asyncio.sleep(wait_time)
        
        return True