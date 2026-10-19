"""
消息模块 - 定义Agent间传递的消息结构和类型
"""
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime
import uuid


class MessageType(Enum):
    """消息类型枚举"""
    TASK = "task"           # 任务输入
    RESULT = "result"       # 执行结果
    ERROR = "error"         # 错误信息
    STATUS = "status"       # 状态更新
    CONTROL = "control"     # 控制信号


class Message:
    """
    Agent间传递的消息对象

    Attributes:
        msg_id: 消息唯一标识
        msg_type: 消息类型
        sender: 发送者名称
        receiver: 接收者名称
        content: 消息内容（字典）
        metadata: 元数据（时间戳、追踪ID等）
    """

    def __init__(
        self,
        msg_type: MessageType,
        sender: str,
        receiver: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.msg_id = str(uuid.uuid4())[:8]
        self.msg_type = msg_type
        self.sender = sender
        self.receiver = receiver
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

        # 设置追踪ID（用于日志追踪）
        if "trace_id" not in self.metadata:
            self.metadata["trace_id"] = str(uuid.uuid4())[:12]

    @property
    def trace_id(self) -> str:
        """获取追踪ID"""
        return self.metadata.get("trace_id", "unknown")

    def reply(self, msg_type: MessageType, content: Dict[str, Any]) -> "Message":
        """
        基于当前消息创建回复消息

        Args:
            msg_type: 回复消息类型
            content: 回复内容

        Returns:
            新的Message对象
        """
        return Message(
            msg_type=msg_type,
            sender=self.receiver,
            receiver=self.sender,
            content=content,
            metadata={
                "trace_id": self.trace_id,
                "reply_to": self.msg_id,
            },
        )

    def forward(self, new_receiver: str, extra_content: Optional[Dict[str, Any]] = None) -> "Message":
        """
        转发消息给新的接收者

        Args:
            new_receiver: 新接收者
            extra_content: 额外添加的内容

        Returns:
            新的Message对象
        """
        content = dict(self.content)
        if extra_content:
            content.update(extra_content)

        return Message(
            msg_type=self.msg_type,
            sender=self.receiver,
            receiver=new_receiver,
            content=content,
            metadata={
                "trace_id": self.trace_id,
                "forwarded_from": self.sender,
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "msg_id": self.msg_id,
            "msg_type": self.msg_type.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return (
            f"Message[{self.msg_id}] {self.msg_type.value}: "
            f"{self.sender} -> {self.receiver}"
        )
