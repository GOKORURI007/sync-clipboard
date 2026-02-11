"""
Clipboard monitoring and management for sync-clipboard
"""

import asyncio
import platform
from typing import Awaitable, Callable

from .exceptions import ClipboardAccessError
from .logging_utils import get_logger


class ClipboardMonitor:
    """Clipboard listener"""

    def __init__(self, callback: Callable[[str], Awaitable[None]]):
        self.callback = callback
        self.cached_content = ''
        self.is_syncing = False
        self.logger = get_logger('clipboard-monitor')
        self._setup_clipboard_backend()

    def _setup_clipboard_backend(self):
        """Set up the clipboard backend"""
        try:
            import pyperclip

            self.clipboard_get = pyperclip.paste
            self.clipboard_set = pyperclip.copy
            self.logger.info(
                f'Clipboard backend initialized, current platform: {platform.system()}'
            )
        except ImportError as e:
            self.logger.error(f'Importing the pyperclip module failed: {e}')
            self.logger.warning('Clipboard functionality is unavailable. Please install pyperclip.')
            self.logger.warning('Current platform: {platform.system()}')
            self.clipboard_get = lambda: ''
            self.clipboard_set = lambda x: None

    async def start_monitoring(self) -> None:
        """Start listening for clipboard changes"""
        try:
            self.cached_content = str(self._safe_clipboard_get())
        except ClipboardAccessError as e:
            self.logger.warning(f'Failed to initialize clipboard contents: {e}')
            self.cached_content = ''

        self.logger.info('Start listening for clipboard changes')

        while True:
            await asyncio.sleep(0.5)  # Check the clipboard every 0.5 seconds

            # If in the process of synchronization, skip the check to prevent loopback
            if self.is_syncing:
                continue

            try:
                current_content = str(self._safe_clipboard_get())

                # Content change detection: Synchronization is triggered only
                # if the content has actually changed and is not empty content
                if self._is_content_changed(current_content):
                    self.cached_content = current_content
                    await self.callback(current_content)

            except ClipboardAccessError as e:
                self.logger.warning(f'Failed to read clipboard. Continue listening: {e}')
                continue
            except Exception as e:
                self.logger.error(
                    f'Unknown error occurred while listening to clipboard: {e}', exc_info=True
                )
                continue

    async def update_clipboard(self, content: str) -> None:
        """Update the local clipboard (anti-loopback)"""
        if content != self.cached_content and content.strip():
            # The synchronization status flag is set to prevent the triggering of new
            # synchronization cycles
            self.is_syncing = True
            try:
                self._safe_clipboard_set(content)
                self.cached_content = content
                self.logger.debug(
                    f'Clipboard content has been updated: '
                    f'{content[:50]}{"..." if len(content) > 50 else ""}'
                )
                # Wait briefly to ensure that the clipboard updates complete
                await asyncio.sleep(0.1)
            except ClipboardAccessError as e:
                self.logger.warning(f'Failed to update the clipboard: {e}')
            except Exception as e:
                self.logger.error(
                    f'Unknown error occurred while updating the clipboard: {e}', exc_info=True
                )
            finally:
                # Ensure that synchronization flags are reset, even in the event of an exception
                self.is_syncing = False

    def _safe_clipboard_get(self) -> str:
        """Securely fetch clipboard contents"""
        try:
            return self.clipboard_get()
        except Exception as e:
            self.logger.warning(f'Failed to access clipboard: {e}')
            raise ClipboardAccessError(f'Unable to read clipboard contents: {e}')

    def _safe_clipboard_set(self, content: str) -> None:
        """Set the clipboard contents securely"""
        try:
            self.clipboard_set(content)
        except Exception as e:
            self.logger.warning(f'Failed to set up clipboard: {e}')
            raise ClipboardAccessError(f'Unable to set clipboard contents: {e}')

    def _is_content_changed(self, new_content: str) -> bool:
        """Detecting if the content has actually changed (removing whitespace)"""
        # Standardize content: Remove leading and trailing whitespace, and unify newline characters
        normalized_current = self.cached_content.strip().replace('\r\n', '\n').replace('\r', '\n')
        normalized_new = new_content.strip().replace('\r\n', '\n').replace('\r', '\n')

        return normalized_current != normalized_new and normalized_new
