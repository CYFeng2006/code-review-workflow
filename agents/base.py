"""
Agent基类 - 所有Agent的抽象基类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from workflow.message import Message, MessageType
from workflow.state import WorkflowState, AgentState

if TYPE_CHECKING:
    from workflow.engine import WorkflowEngine


class BaseAgent(ABC):
    """
    Agent抽象基类

    所有具体Agent都需要继承此类并实现 execute 方法。
    Agent通过消息与其他Agent通信，通过WorkflowState共享数据。
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._engine: Optional["WorkflowEngine"] = None
        self._state: Optional[WorkflowState] = None
        self._inbox: List[Message] = []

    @property
    def engine(self) -> "WorkflowEngine":
        """获取关联的Workflow引擎"""
        if self._engine is None:
            raise RuntimeError(f"Agent '{self.name}' 未注册到任何Workflow引擎")
        return self._engine

    @property
    def state(self) -> WorkflowState:
        """获取Workflow状态"""
        if self._state is None:
            raise RuntimeError(f"Agent '{self.name}' 未关联任何Workflow状态")
        return self._state

    @property
    def logger(self):
        """获取日志记录器"""
        return self.engine.logger

    def _register(self, engine: "WorkflowEngine", state: WorkflowState):
        """注册到Workflow引擎（由引擎调用）"""
        self._engine = engine
        self._state = state

    # --- 消息收发 ---

    def receive_message(self, message: Message):
        """接收消息（放入收件箱）"""
        self._inbox.append(message)

    def get_message(self) -> Optional[Message]:
        """从收件箱获取一条消息"""
        if self._inbox:
            return self._inbox.pop(0)
        return None

    def send_message(self, receiver: str, content: Dict[str, Any],
                     msg_type: MessageType = MessageType.TASK) -> Message:
        """
        向另一个Agent发送消息

        Args:
            receiver: 接收者Agent名称
            content: 消息内容
            msg_type: 消息类型

        Returns:
            发送的消息对象
        """
        message = Message(
            msg_type=msg_type,
            sender=self.name,
            receiver=receiver,
            content=content,
        )
        self.engine.deliver_message(message)
        return message

    def reply_to(self, original_msg: Message, content: Dict[str, Any],
                 msg_type: MessageType = MessageType.RESULT) -> Message:
        """
        回复一条消息

        Args:
            original_msg: 原始消息
            content: 回复内容
            msg_type: 回复消息类型

        Returns:
            回复消息对象
        """
        reply_msg = original_msg.reply(msg_type, content)
        self.engine.deliver_message(reply_msg)
        return reply_msg

    # --- 生命周期 ---

    def on_start(self):
        """Agent开始执行前的钩子方法，可重写"""
        pass

    def on_end(self):
        """Agent执行结束后的钩子方法，可重写"""
        pass

    def on_error(self, error: Exception):
        """Agent出错时的钩子方法，可重写"""
        pass

    @abstractmethod
    def execute(self, input_data: Any) -> Any:
        """
        执行Agent的核心逻辑（子类必须实现）

        Args:
            input_data: 输入数据

        Returns:
            输出结果
        """
        pass

    # --- 便捷方法 ---

    def log_info(self, message: str, **kwargs):
        """记录INFO级别日志"""
        self.logger.info(message, component=self.name, **kwargs)

    def log_debug(self, message: str, **kwargs):
        """记录DEBUG级别日志"""
        self.logger.debug(message, component=self.name, **kwargs)

    def log_warning(self, message: str, **kwargs):
        """记录WARNING级别日志"""
        self.logger.warning(message, component=self.name, **kwargs)

    def log_error(self, message: str, **kwargs):
        """记录ERROR级别日志"""
        self.logger.error(message, component=self.name, **kwargs)

    def set_state_data(self, key: str, value: Any):
        """设置全局状态数据"""
        self.state.set(key, value)

    def get_state_data(self, key: str, default: Any = None) -> Any:
        """获取全局状态数据"""
        return self.state.get(key, default)

    def __repr__(self) -> str:
        return f"Agent[{self.name}]"
