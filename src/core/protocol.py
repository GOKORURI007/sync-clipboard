#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Message protocol and data structures for sync-clipboard
"""
import json
import time
from dataclasses import dataclass, asdict

from .exceptions import MessageFormatError
from .logging_utils import get_logger


@dataclass
class Message:
    """简化的消息协议类"""
    type: str  # "clipboard_update", "client_hello", "error"
    sender_id: str
    content: str = ""
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        
        # 验证消息类型
        valid_types = {"clipboard_update", "client_hello", "error"}
        if self.type not in valid_types:
            logger = get_logger("protocol")
            logger.warning(f"无效的消息类型: {self.type}")
    
    def to_json(self) -> str:
        """序列化为JSON"""
        try:
            return json.dumps(asdict(self))
        except (TypeError, ValueError) as e:
            logger = get_logger("protocol")
            logger.error(f"消息序列化失败: {e}")
            raise MessageFormatError(f"无法序列化消息: {e}")
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """从JSON反序列化"""
        logger = get_logger("protocol")
        
        if not json_str or not json_str.strip():
            logger.warning("收到空消息")
            raise MessageFormatError("消息内容为空")
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            raise MessageFormatError(f"无效的JSON格式: {e}")
        
        # 验证必需字段
        required_fields = {"type", "sender_id"}
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            logger.error(f"消息缺少必需字段: {missing_fields}")
            raise MessageFormatError(f"消息缺少必需字段: {missing_fields}")
        
        try:
            return cls(**data)
        except TypeError as e:
            logger.error(f"消息字段类型错误: {e}")
            raise MessageFormatError(f"消息字段类型错误: {e}")