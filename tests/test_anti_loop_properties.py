#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for anti-loop mechanism
Tests Properties 3, 11, and 12 from the design document
"""
import asyncio
from contextlib import contextmanager
from typing import List
from unittest.mock import patch

import pytest
from hypothesis import assume, given, HealthCheck, settings, strategies as st
from hypothesis.strategies import booleans, integers, text

from src.sync_clipboard_cli import ClipboardMonitor, Message, SyncClient, SyncServer


class MockWebSocket:
    """Mock WebSocket connection for testing"""
    
    def __init__(self, remote_address=("127.0.0.1", 12345)):
        self.remote_address = remote_address
        self.sent_messages: List[str] = []
        self.closed = False
    
    async def send(self, message: str):
        if self.closed:
            raise Exception("Connection closed")
        self.sent_messages.append(message)
    
    def close(self):
        self.closed = True


@contextmanager
def mock_clipboard():
    """Context manager for mocking clipboard"""
    with patch('pyperclip.paste') as mock_paste, \
         patch('pyperclip.copy') as mock_copy:
        mock_paste.return_value = ""
        yield mock_paste, mock_copy


def run_async(coro):
    """Helper to run async functions in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestAntiLoopProperties:
    """Property-based tests for anti-loop mechanisms"""
    
    @given(
        content=text(min_size=1, max_size=100),
        sender_hostname=text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz'),
        client_hostnames=st.lists(
            text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz'), 
            min_size=1, max_size=5, unique=True
        )
    )
    @settings(max_examples=100, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_3_anti_loop_broadcast(self, content, sender_hostname, client_hostnames):
        """
        Property 3: Anti-loop broadcast
        For any message from a client to server, server broadcast should exclude the sender,
        ensuring sender doesn't receive their own message
        **Validates: Requirements 1.3, 3.1**
        """
        async def _test():
            with mock_clipboard() as (mock_paste, mock_copy):
                # Ensure sender is different from clients
                assume(sender_hostname not in client_hostnames)
                assume(len(content.strip()) > 0)
                
                # Create server
                server = SyncServer("127.0.0.1", 8765, "test_server")
                
                # Create mock websockets for clients
                client_websockets = {}
                for hostname in client_hostnames:
                    ws = MockWebSocket()
                    client_websockets[hostname] = ws
                    server.add_client(ws, hostname)
                
                # Create sender websocket (not in client list to simulate external sender)
                sender_ws = MockWebSocket()
                server.add_client(sender_ws, sender_hostname)
                
                # Broadcast message from sender
                await server.broadcast_clipboard_update(content, sender_ws)
                
                # Verify sender websocket didn't receive the message
                assert len(sender_ws.sent_messages) == 0, f"Sender {sender_hostname} should not receive their own message"
                
                # Verify all other clients received the message
                for hostname, ws in client_websockets.items():
                    if hostname != sender_hostname:
                        assert len(ws.sent_messages) == 1, f"Client {hostname} should receive the broadcast"
                        
                        # Parse and verify message content
                        message = Message.from_json(ws.sent_messages[0])
                        assert message.content == content
                        assert message.sender_id == sender_hostname
                        assert message.type == "clipboard_update"
        
        run_async(_test())
    
    @given(
        initial_content=text(max_size=50),
        new_content=text(min_size=1, max_size=100),
        sync_operations=integers(min_value=1, max_value=3)
    )
    @settings(max_examples=100, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_11_sync_state_anti_loop(self, initial_content, new_content, sync_operations):
        """
        Property 11: Sync state anti-loop
        For any node updating local clipboard, system should mark as syncing state
        to prevent that update from triggering new sync loop
        **Validates: Requirements 3.2**
        """
        async def _test():
            with mock_clipboard() as (mock_paste, mock_copy):
                assume(new_content.strip() != initial_content.strip())
                assume(len(new_content.strip()) > 0)
                
                mock_paste.return_value = initial_content
                
                callback_calls = []
                
                async def test_callback(content: str):
                    callback_calls.append(content)
                
                # Create clipboard monitor
                monitor = ClipboardMonitor(test_callback)
                
                # Simulate updating clipboard during sync
                await monitor.update_clipboard(new_content)
                
                # Verify sync state was set during update
                # The is_syncing flag should prevent callback from being triggered
                # by the clipboard change we just made
                
                # Simulate clipboard monitoring check immediately after update
                # This should not trigger callback because is_syncing should be False by now
                # but the content should be updated
                assert monitor.cached_content == new_content
                
                # Verify that multiple sync operations don't cause loops
                for i in range(sync_operations):
                    test_content = f"{new_content}_iteration_{i}"
                    await monitor.update_clipboard(test_content)
                    assert monitor.cached_content == test_content
                
                # The callback should not have been called during sync operations
                # because they were initiated by update_clipboard (sync operations)
                assert len(callback_calls) == 0, "Sync operations should not trigger callbacks"
        
        run_async(_test())
    
    @given(
        content_variations=st.lists(
            text(min_size=0, max_size=100),
            min_size=2, max_size=10
        )
    )
    @settings(max_examples=100, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_12_content_change_detection(self, content_variations):
        """
        Property 12: Content change detection
        For any clipboard content check, system should only trigger sync when content
        actually changes, identical content should not trigger repeated sync
        **Validates: Requirements 3.3**
        """
        async def _test():
            with mock_clipboard() as (mock_paste, mock_copy):
                callback_calls = []
                
                async def test_callback(content: str):
                    callback_calls.append(content)
                
                monitor = ClipboardMonitor(test_callback)
                
                # Track the last content that would have triggered a callback
                last_callback_content = ""
                
                for content in content_variations:
                    # Set clipboard content
                    mock_paste.return_value = content
                    
                    # Simulate the monitoring check (like the actual implementation)
                    if not monitor.is_syncing:
                        current_clipboard = str(mock_paste())
                        if (current_clipboard != monitor.cached_content and
                            current_clipboard.strip() and
                            monitor._is_content_changed(current_clipboard)):
                            monitor.cached_content = current_clipboard
                            await monitor.callback(current_clipboard)
                            last_callback_content = current_clipboard
                
                # Verify no duplicate consecutive content in callbacks
                # This is the core property: no identical consecutive callbacks should occur
                for i in range(1, len(callback_calls)):
                    prev_normalized = callback_calls[i-1].strip().replace('\r\n', '\n').replace('\r', '\n')
                    curr_normalized = callback_calls[i].strip().replace('\r\n', '\n').replace('\r', '\n')
                    assert prev_normalized != curr_normalized, \
                        f"Duplicate consecutive content detected: '{prev_normalized}' == '{curr_normalized}'"
                
                # Verify that all callbacks contain non-empty content (after normalization)
                for callback_content in callback_calls:
                    normalized = callback_content.strip().replace('\r\n', '\n').replace('\r', '\n')
                    assert normalized, f"Empty content should not trigger callback: '{callback_content}'"
        
        run_async(_test())
    
    @given(
        hostname=text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz'),
        content=text(min_size=1, max_size=100)
    )
    @settings(max_examples=100, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_3_client_ignores_own_messages(self, hostname, content):
        """
        Property 3 (Client side): Anti-loop message handling
        For any node receiving a message, if the message was sent by itself,
        the node should ignore that message
        **Validates: Requirements 3.4**
        """
        async def _test():
            with mock_clipboard() as (mock_paste, mock_copy):
                assume(len(content.strip()) > 0)
                
                mock_paste.return_value = ""
                
                # Create client
                client = SyncClient("127.0.0.1", 8765, hostname)
                
                # Create message from same hostname (own message)
                own_message = Message(
                    type="clipboard_update",
                    sender_id=hostname,  # Same as client hostname
                    content=content
                )
                
                # Create message from different hostname
                other_message = Message(
                    type="clipboard_update", 
                    sender_id="other_host",
                    content=content
                )
                
                # Handle own message - should be ignored
                await client.handle_server_message(own_message)
                
                # Verify clipboard was not updated (no copy call)
                mock_copy.assert_not_called()
                
                # Reset mock
                mock_copy.reset_mock()
                
                # Handle message from other host - should be processed
                await client.handle_server_message(other_message)
                
                # Verify clipboard was updated
                mock_copy.assert_called_once_with(content)
        
        run_async(_test())


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])