#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Command-line interface for sync-clipboard
"""

import datetime
import signal
import sys

import click

from src.compat.clipboard_sync import ClipboardSync
from src.core.exceptions import ClipboardConnectionError, ConfigurationError, SyncClipboardError
from src.core.logging_utils import get_logger
from src.core.version import __version__


def cli_log(message: str) -> None:
    """CLI logging function that outputs to standard output"""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{timestamp}] {message}', flush=True)


def signal_handler(signum, frame):
    """Signal handler for graceful shutdown"""
    logger = get_logger('cli')
    logger.info('Received shutdown signal, stopping service...')
    sys.exit(0)


@click.command()
@click.option(
    '--mode',
    '-m',
    type=click.Choice(['server', 'client'], case_sensitive=False),
    required=True,
    help='Run mode: server or client',
)
@click.option('--host', '-h', default='127.0.0.1', help='Server host address (default: 127.0.0.1)')
@click.option('--port', '-p', default=8765, type=int, help='Server port number (default: 8765)')
@click.version_option(
    __version__, '--version', '-v', message='SyncClipboard %(version)s - Cross-device clipboard sync tool'
)
def main(mode, host, port):
    """
    SyncClipboard - Cross-device clipboard synchronization tool

    Supports Server-Client architecture for clipboard content synchronization:

    \b
    Server mode:
      - Acts as a central hub to receive and broadcast clipboard content
      - Monitors local clipboard changes and participates in synchronization

    \b
    Client mode:
      - Connects to the server for clipboard synchronization
      - Supports automatic reconnection

    \b
    Examples:
      Start server: sync-clipboard --mode server --host 0.0.0.0 --port 8765
      Start client: sync-clipboard --mode client --host 192.168.1.100 --port 8765
    """

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)

    # Initialize logger
    logger = get_logger('cli', cli_log)

    # Display startup information
    logger.info(f'SyncClipboard {__version__} - Starting {mode} mode')
    logger.info(f'Server address: {host}:{port}')
    logger.info('Press Ctrl+C to exit')
    logger.info('-' * 40)

    # Validate configuration parameters
    try:
        if not host or not host.strip():
            raise ConfigurationError('Host address cannot be empty')
        if not (1 <= port <= 65535):
            raise ConfigurationError(f'Port must be between 1-65535, current value: {port}')
    except ConfigurationError as e:
        logger.error(f'Configuration error: {e}')
        sys.exit(1)

    # Create synchronization instance with CLI log callback
    sync_clipboard = None
    try:
        sync_clipboard = ClipboardSync(host, port, mode, log_callback=cli_log)
        sync_clipboard.start_sync()
    except KeyboardInterrupt:
        logger.info('Received keyboard interrupt, stopping service...')
    except ClipboardConnectionError as e:
        logger.error(f'Connection error: {e}')
        sys.exit(1)
    except ConfigurationError as e:
        logger.error(f'Configuration error: {e}')
        sys.exit(1)
    except SyncClipboardError as e:
        logger.error(f'Clipboard synchronization error: {e}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'Unknown runtime error: {e}', exc_info=True)
        sys.exit(1)
    finally:
        # Ensure graceful shutdown
        if sync_clipboard:
            try:
                sync_clipboard.stop_sync()
                logger.info('Service stopped safely')
            except Exception as e:
                logger.error(f'Error while stopping service: {e}')
        logger.info('Program exited')


if __name__ == '__main__':
    main()
