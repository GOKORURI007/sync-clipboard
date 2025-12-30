#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Command-line interface for sync-clipboard
"""
import click
import sys
import signal
import datetime

from ..core.version import __version__
from ..core.logging_utils import get_logger
from ..core.exceptions import SyncClipboardError, ConnectionError, ConfigurationError
from ..compat.clipboard_sync import ClipboardSync


def cli_log(message: str) -> None:
    """CLI 日志输出函数，输出到标准输出"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def signal_handler(signum, frame):
    """信号处理函数，用于优雅退出"""
    logger = get_logger("cli")
    logger.info("接收到退出信号，正在停止服务...")
    sys.exit(0)


@click.command()
@click.option('--mode', '-m',
              type=click.Choice(['server', 'client'], case_sensitive=False),
              required=True,
              help='运行模式: server (服务端) 或 client (客户端)')
@click.option('--host', '-h', default='127.0.0.1', 
              help='服务器主机地址 (默认: 127.0.0.1)')
@click.option('--port', '-p', default=8765, type=int, 
              help='服务器端口号 (默认: 8765)')
@click.version_option(__version__, '--version', '-v',
                      message="SyncClipboard %(version)s - 跨设备剪贴板同步工具")
def main(mode, host, port):
    """
    SyncClipboard - 跨设备剪贴板同步工具
    
    支持 Server-Client 架构的剪贴板内容同步:
    
    \b
    服务端模式 (server):
      - 作为中央枢纽接收和广播剪贴板内容
      - 同时监听本地剪贴板变化并参与同步
      
    \b  
    客户端模式 (client):
      - 连接到服务端进行剪贴板同步
      - 支持自动重连功能
    
    \b
    示例:
      启动服务端: sync-clipboard --mode server --host 0.0.0.0 --port 8765
      启动客户端: sync-clipboard --mode client --host 192.168.1.100 --port 8765
    """
    
    # 设置信号处理器，支持优雅退出
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    # 初始化日志记录器
    logger = get_logger("cli", cli_log)
    
    # 显示启动信息
    logger.info(f"SyncClipboard {__version__} - 启动 {mode} 模式")
    logger.info(f"服务器地址: {host}:{port}")
    logger.info("按 Ctrl+C 退出程序")
    logger.info("-" * 40)
    
    # 验证配置参数
    try:
        if not host or not host.strip():
            raise ConfigurationError("主机地址不能为空")
        if not (1 <= port <= 65535):
            raise ConfigurationError(f"端口号必须在 1-65535 范围内，当前值: {port}")
    except ConfigurationError as e:
        logger.error(f"配置错误: {e}")
        sys.exit(1)
    
    # 创建同步实例，使用 CLI 日志函数
    sync_clipboard = None
    try:
        sync_clipboard = ClipboardSync(host, port, mode, log_callback=cli_log)
        sync_clipboard.start_sync()
    except KeyboardInterrupt:
        logger.info("接收到键盘中断信号，正在停止服务...")
    except ConnectionError as e:
        logger.error(f"连接错误: {e}")
        sys.exit(1)
    except ConfigurationError as e:
        logger.error(f"配置错误: {e}")
        sys.exit(1)
    except SyncClipboardError as e:
        logger.error(f"同步剪贴板错误: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"运行时发生未知错误: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # 确保优雅退出
        if sync_clipboard:
            try:
                sync_clipboard.stop_sync()
                logger.info("服务已安全停止")
            except Exception as e:
                logger.error(f"停止服务时出现错误: {e}")
        logger.info("程序已退出")


if __name__ == "__main__":
    main()