#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration tests for SyncClipboard Server-Client communication
Tests basic communication and multi-client scenarios
"""
import asyncio
import platform
import time
from unittest.mock import patch, MagicMock
from typing import List, Dict, Optional
import pytest

from src.server.sync_server import SyncServer
from src.client.sync_client import SyncClient
from src.core.protocol import Message
from src.core.clipboard import ClipboardMonitor


class MockClipboard:
    """Mock clipboard for testing"""
    
    def __init__(self, initial_content: str = ""):
        self.content = initial_content
        self.access_count = 0
    
    def paste(self) -> str:
        self.access_count += 1
        return self.content
    
    def copy(self, content: str) -> None:
        self.content = content


class TestServerClientIntegration:
    """Integration tests for Server-Client communication"""
    
    @pytest.fixture
    def mock_clipboard_backend(self):
        """Mock clipboard backend for all tests"""
        mock_clipboard = MockClipboard()
        
        with patch('pyperclip.paste', side_effect=mock_clipboard.paste), \
             patch('pyperclip.copy', side_effect=mock_clipboard.copy):
            yield mock_clipboard
    
    @pytest.fixture
    def event_loop(self):
        """Create event loop for async tests"""
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()
    
    def test_server_client_basic_communication(self, mock_clipboard_backend, event_loop):
        """
        Test basic Server-Client communication
        Validates Requirements: 1.2 (server broadcasts to clients), 2.3 (client receives updates)
        """
        async def _test():
            # Setup
            server_hostname = "test_server"
            client_hostname = "test_client"
            test_content = "integration_test_content"
            
            # Create server (without starting WebSocket server for simpler testing)
            server_logs = []
            server = SyncServer(
                host="127.0.0.1",
                port=18765,
                hostname=server_hostname,
                log_callback=lambda msg: server_logs.append(msg)
            )
            
            # Create client (without connecting to actual server)
            client_logs = []
            client = SyncClient(
                server_host="127.0.0.1",
                server_port=18765,
                hostname=client_hostname,
                auto_reconnect=False,
                log_callback=lambda msg: client_logs.append(msg)
            )
            
            # Test 1: Client sending clipboard update (simulated)
            # Create a message that would be sent from client to server
            client_message = Message(
                type="clipboard_update",
                sender_id=client_hostname,
                content=test_content
            )
            
            # Simulate server receiving and processing the message
            # This tests the server's message handling logic
            await server._handle_clipboard_update(client_message, None)
            
            # Verify server logged receiving the message
            assert any("收到" in log and test_content[:20] in log for log in server_logs), \
                "Server should log receiving clipboard update"
            
            # Test 2: Server broadcasting to client (simulated)
            # Create a message that would be broadcast from server to client
            server_message = Message(
                type="clipboard_update",
                sender_id=server_hostname,
                content=test_content
            )
            
            # Simulate client receiving and processing the message
            await client.handle_server_message(server_message)
            
            # Verify client updated local clipboard
            assert mock_clipboard_backend.content == test_content, \
                "Client should update local clipboard with server broadcast"
            
            # Verify client logged receiving the message
            assert any("收到" in log and test_content[:20] in log for log in client_logs), \
                "Client should log receiving clipboard update"
            
            # Test 3: Anti-loop behavior - client ignores own messages
            mock_clipboard_backend.content = ""  # Reset clipboard
            
            own_message = Message(
                type="clipboard_update",
                sender_id=client_hostname,  # Same as client hostname
                content="should_be_ignored"
            )
            
            await client.handle_server_message(own_message)
            
            # Verify clipboard was not updated (message was ignored)
            assert mock_clipboard_backend.content == "", \
                "Client should ignore messages from itself"
        
        loop = event_loop
        loop.run_until_complete(_test())
    
    def test_multi_client_scenario(self, mock_clipboard_backend, event_loop):
        """
        Test multi-client scenario with message broadcasting
        Validates Requirements: 1.2 (server broadcasts), 1.3 (excludes sender), 2.3 (clients receive)
        """
        async def _test():
            # Setup
            server_hostname = "test_server"
            client_hostnames = ["client_1", "client_2", "client_3"]
            test_content = "multi_client_test_content"
            
            # Create server
            server_logs = []
            server = SyncServer(
                host="127.0.0.1",
                port=18766,
                hostname=server_hostname,
                log_callback=lambda msg: server_logs.append(msg)
            )
            
            # Create multiple mock websockets and add them as clients
            mock_websockets = {}
            for hostname in client_hostnames:
                # Create a simple mock websocket
                class MockWebSocket:
                    def __init__(self, hostname):
                        self.hostname = hostname
                        self.sent_messages = []
                        self.closed = False
                    
                    async def send(self, message):
                        if not self.closed:
                            self.sent_messages.append(message)
                
                mock_ws = MockWebSocket(hostname)
                mock_websockets[hostname] = mock_ws
                server.add_client(mock_ws, hostname)
            
            # Verify all clients are registered
            assert len(server.clients) == len(client_hostnames), \
                f"Server should have {len(client_hostnames)} connected clients"
            
            # Test: Server broadcasts message, excluding sender
            sender_hostname = client_hostnames[0]
            sender_ws = mock_websockets[sender_hostname]
            
            # Broadcast message with sender exclusion
            await server.broadcast_clipboard_update(test_content, sender_ws)
            
            # Verify sender didn't receive the message (anti-loop)
            assert len(sender_ws.sent_messages) == 0, \
                "Sender should not receive its own message"
            
            # Verify other clients received the message
            for hostname in client_hostnames[1:]:
                ws = mock_websockets[hostname]
                assert len(ws.sent_messages) == 1, \
                    f"Client {hostname} should receive the broadcast message"
                
                # Verify message content
                message = Message.from_json(ws.sent_messages[0])
                assert message.content == test_content, \
                    f"Client {hostname} should receive correct content"
                assert message.sender_id == sender_hostname, \
                    f"Message should identify correct sender"
            
            # Test: Server broadcasts without sender (server-originated message)
            server_content = "server_broadcast_content"
            
            # Clear previous messages
            for ws in mock_websockets.values():
                ws.sent_messages.clear()
            
            # Server broadcasts (no sender exclusion)
            await server.broadcast_clipboard_update(server_content)
            
            # Verify all clients received server broadcast
            for hostname in client_hostnames:
                ws = mock_websockets[hostname]
                assert len(ws.sent_messages) == 1, \
                    f"Client {hostname} should receive server broadcast"
                
                message = Message.from_json(ws.sent_messages[0])
                assert message.content == server_content, \
                    f"Client {hostname} should receive correct server content"
                assert message.sender_id == server_hostname, \
                    f"Message should identify server as sender"
        
        loop = event_loop
        loop.run_until_complete(_test())
    
    def test_client_connection_management(self, mock_clipboard_backend, event_loop):
        """
        Test client connection and disconnection management
        Validates Requirements: 1.4 (maintain client list), 1.5 (remove disconnected clients)
        """
        async def _test():
            # Setup
            server_hostname = "test_server"
            client_hostnames = ["client_1", "client_2", "client_3"]
            
            # Create server
            server_logs = []
            server = SyncServer(
                host="127.0.0.1",
                port=18767,
                hostname=server_hostname,
                log_callback=lambda msg: server_logs.append(msg)
            )
            
            # Initially no clients
            assert len(server.clients) == 0, "Server should start with no clients"
            
            # Create mock websockets and add clients
            mock_websockets = []
            for hostname in client_hostnames:
                class MockWebSocket:
                    def __init__(self, hostname):
                        self.hostname = hostname
                        self.sent_messages = []
                
                mock_ws = MockWebSocket(hostname)
                mock_websockets.append(mock_ws)
                
                # Add client to server
                server.add_client(mock_ws, hostname)
                
                # Verify client count increases
                expected_count = len(mock_websockets)
                assert len(server.clients) == expected_count, \
                    f"Server should have {expected_count} clients after adding {hostname}"
                
                # Verify hostname is stored correctly
                stored_hostname = server.get_client_hostname(mock_ws)
                assert stored_hostname == hostname, \
                    f"Stored hostname should be {hostname}, got {stored_hostname}"
            
            # Verify all clients are connected
            assert len(server.clients) == len(client_hostnames), \
                f"Server should have {len(client_hostnames)} total clients"
            
            # Test removing clients one by one
            for i, (mock_ws, hostname) in enumerate(zip(mock_websockets, client_hostnames)):
                # Remove client
                server.remove_client(mock_ws)
                
                # Verify client count decreases
                expected_count = len(client_hostnames) - i - 1
                assert len(server.clients) == expected_count, \
                    f"Server should have {expected_count} clients after removing {hostname}"
                
                # Verify removed client hostname returns None
                assert server.get_client_hostname(mock_ws) is None, \
                    f"Removed client {hostname} should return None for hostname"
            
            # Verify no clients remain
            assert len(server.clients) == 0, "Server should have no clients after removing all"
        
        loop = event_loop
        loop.run_until_complete(_test())
    
    def test_message_protocol_integration(self, mock_clipboard_backend, event_loop):
        """
        Test message protocol serialization/deserialization in integration context
        Validates Requirements: 7.2 (JSON serialization), 7.3 (message types)
        """
        async def _test():
            # Test message creation and serialization
            test_content = "protocol_test_content"
            sender_id = "test_sender"
            
            # Create message
            message = Message(
                type="clipboard_update",
                sender_id=sender_id,
                content=test_content
            )
            
            # Serialize to JSON
            json_str = message.to_json()
            assert isinstance(json_str, str), "Message should serialize to string"
            assert test_content in json_str, "Serialized message should contain content"
            assert sender_id in json_str, "Serialized message should contain sender_id"
            
            # Deserialize from JSON
            deserialized = Message.from_json(json_str)
            assert deserialized.type == "clipboard_update", "Deserialized type should match"
            assert deserialized.sender_id == sender_id, "Deserialized sender_id should match"
            assert deserialized.content == test_content, "Deserialized content should match"
            assert deserialized.timestamp > 0, "Deserialized message should have timestamp"
            
            # Test client hello message
            hello_message = Message(
                type="client_hello",
                sender_id="test_client"
            )
            
            hello_json = hello_message.to_json()
            hello_deserialized = Message.from_json(hello_json)
            assert hello_deserialized.type == "client_hello", "Hello message type should match"
            assert hello_deserialized.content == "", "Hello message should have empty content"
        
        loop = event_loop
        loop.run_until_complete(_test())


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])