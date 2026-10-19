"""
状态模块 - 定义Workflow和Agent的状态管理
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime


class AgentState(Enum):
    """Agent执行状态"""
    IDLE = "idle"           # 空闲
    RUNNING = "running"     # 运行中
    SUCCESS = "success"     # 成功
    FAILED = "failed"       # 失败
    SKIPPED = "skipped"     # 跳过


class WorkflowStatus(Enum):
    """Workflow整体状态"""
    PENDING = "pending"     # 待执行
    RUNNING = "running"     # 运行中
    COMPLETED = "completed" # 成功完成
    FAILED = "failed"       # 失败
    CANCELLED = "cancelled" # 取消


class WorkflowState:
    """
    Workflow全局状态管理器

    负责存储和管理整个Workflow的共享数据，
    所有Agent都可以读写共享状态以实现协作。
    """

    def __init__(self, workflow_name: str):
        self.workflow_name = workflow_name
        self.status = WorkflowStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

        # 全局共享数据
        self._global_data: Dict[str, Any] = {}

        # 各Agent的输出结果
        self._agent_outputs: Dict[str, Any] = {}

        # 各Agent的执行状态
        self._agent_states: Dict[str, AgentState] = {}

        # 执行历史记录
        self._history: List[Dict[str, Any]] = []

    def start(self):
        """标记Workflow开始执行"""
        self.status = WorkflowStatus.RUNNING
        self.started_at = datetime.now()
        self._add_history("workflow_started", {"workflow": self.workflow_name})

    def complete(self, success: bool = True):
        """标记Workflow完成"""
        self.status = WorkflowStatus.COMPLETED if success else WorkflowStatus.FAILED
        self.completed_at = datetime.now()
        self._add_history("workflow_completed", {"success": success})

    def cancel(self):
        """取消Workflow"""
        self.status = WorkflowStatus.CANCELLED
        self.completed_at = datetime.now()
        self._add_history("workflow_cancelled", {})

    # --- 全局数据 ---

    def set(self, key: str, value: Any):
        """设置全局数据"""
        self._global_data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取全局数据"""
        return self._global_data.get(key, default)

    @property
    def global_data(self) -> Dict[str, Any]:
        """获取全部全局数据的副本"""
        return dict(self._global_data)

    # --- Agent输出 ---

    def set_agent_output(self, agent_name: str, output: Any):
        """记录Agent的输出结果"""
        self._agent_outputs[agent_name] = output

    def get_agent_output(self, agent_name: str, default: Any = None) -> Any:
        """获取Agent的输出结果"""
        return self._agent_outputs.get(agent_name, default)

    @property
    def agent_outputs(self) -> Dict[str, Any]:
        """获取所有Agent输出的副本"""
        return dict(self._agent_outputs)

    # --- Agent状态 ---

    def set_agent_state(self, agent_name: str, state: AgentState):
        """设置Agent执行状态"""
        self._agent_states[agent_name] = state
        self._add_history("agent_state_changed", {
            "agent": agent_name,
            "state": state.value,
        })

    def get_agent_state(self, agent_name: str) -> AgentState:
        """获取Agent执行状态"""
        return self._agent_states.get(agent_name, AgentState.IDLE)

    @property
    def agent_states(self) -> Dict[str, AgentState]:
        """获取所有Agent状态"""
        return dict(self._agent_states)

    # --- 历史记录 ---

    def _add_history(self, event: str, data: Dict[str, Any]):
        """添加历史记录"""
        self._history.append({
            "event": event,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        })

    @property
    def history(self) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return list(self._history)

    # --- 统计信息 ---

    def summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        duration = None
        if self.started_at and self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            duration = (datetime.now() - self.started_at).total_seconds()

        return {
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": duration,
            "agent_states": {k: v.value for k, v in self._agent_states.items()},
            "history_count": len(self._history),
        }

    def __repr__(self) -> str:
        return f"WorkflowState[{self.workflow_name}] status={self.status.value}"
