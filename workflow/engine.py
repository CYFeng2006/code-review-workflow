"""
Workflow引擎 - 流程编排与执行控制核心

支持：
- 顺序执行
- 条件分支
- 循环重试
- 并行执行
- 错误处理与恢复
- 状态管理
"""
from typing import Any, Callable, Dict, List, Optional, Union
from datetime import datetime

from .message import Message, MessageType
from .state import WorkflowState, AgentState, WorkflowStatus
from .logger import WorkflowLogger, LogLevel


class WorkflowEngine:
    """
    Workflow流程编排引擎

    负责管理Agent注册、流程定义、消息传递和执行控制。
    """

    def __init__(self, name: str, log_level: LogLevel = LogLevel.INFO):
        self.name = name
        self.logger = WorkflowLogger(level=log_level)
        self.state = WorkflowState(name)

        # 注册的Agent
        self._agents: Dict[str, Any] = {}

        # 流程定义：步骤列表
        self._steps: List[Dict[str, Any]] = []

        # 当前执行到的步骤索引
        self._current_step: int = -1

        # 最大重试次数
        self.max_retries = 3

        # 错误处理策略
        self.error_strategy = "stop"  # stop, skip, retry

    # --- Agent注册 ---

    def register_agent(self, agent) -> "WorkflowEngine":
        """
        注册一个Agent

        Args:
            agent: Agent实例（继承BaseAgent）

        Returns:
            self（支持链式调用）
        """
        if agent.name in self._agents:
            raise ValueError(f"Agent '{agent.name}' 已存在")

        agent._register(self, self.state)
        self._agents[agent.name] = agent
        self.state.set_agent_state(agent.name, AgentState.IDLE)
        self.logger.info(f"注册Agent: {agent.name}", component="engine")
        return self

    def get_agent(self, name: str):
        """获取已注册的Agent"""
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' 未注册")
        return self._agents[name]

    @property
    def agents(self) -> Dict[str, Any]:
        """获取所有已注册Agent"""
        return dict(self._agents)

    # --- 流程定义 ---

    def add_step(
        self,
        agent_name: str,
        input_mapper: Optional[Callable[[Any], Any]] = None,
        output_mapper: Optional[Callable[[Any], Any]] = None,
        condition: Optional[Callable[[WorkflowState], bool]] = None,
        name: Optional[str] = None,
    ) -> "WorkflowEngine":
        """
        添加一个执行步骤

        Args:
            agent_name: 执行该步骤的Agent名称
            input_mapper: 输入映射函数（从全局状态/前序输出映射到本步骤输入）
            output_mapper: 输出映射函数（将本步骤输出映射到全局状态）
            condition: 条件函数，返回True才执行该步骤
            name: 步骤名称（可选，默认使用agent_name）

        Returns:
            self（支持链式调用）
        """
        if agent_name not in self._agents:
            raise ValueError(f"Agent '{agent_name}' 未注册，无法添加步骤")

        step = {
            "name": name or agent_name,
            "agent_name": agent_name,
            "input_mapper": input_mapper,
            "output_mapper": output_mapper,
            "condition": condition,
            "retry_count": 0,
        }
        self._steps.append(step)
        self.logger.info(f"添加步骤: {step['name']} (Agent: {agent_name})", component="engine")
        return self

    def add_parallel_step(
        self,
        agent_names: List[str],
        name: Optional[str] = None,
    ) -> "WorkflowEngine":
        """
        添加一个并行执行步骤

        Args:
            agent_names: 并行执行的Agent名称列表
            name: 步骤名称

        Returns:
            self（支持链式调用）
        """
        for agent_name in agent_names:
            if agent_name not in self._agents:
                raise ValueError(f"Agent '{agent_name}' 未注册")

        step = {
            "name": name or f"parallel({','.join(agent_names)})",
            "type": "parallel",
            "agent_names": agent_names,
            "condition": None,
        }
        self._steps.append(step)
        self.logger.info(f"添加并行步骤: {step['name']}", component="engine")
        return self

    # --- 消息传递 ---

    def deliver_message(self, message: Message):
        """
        投递消息到目标Agent

        Args:
            message: 消息对象
        """
        if message.receiver not in self._agents:
            self.logger.warning(
                f"消息投递失败: 目标Agent '{message.receiver}' 不存在",
                component="engine",
            )
            return

        target_agent = self._agents[message.receiver]
        target_agent.receive_message(message)
        self.logger.debug(
            f"消息投递: {message.sender} -> {message.receiver} ({message.msg_type.value})",
            component="engine",
            trace_id=message.trace_id,
        )

    # --- 执行控制 ---

    def run(self, initial_input: Any = None) -> WorkflowState:
        """
        启动Workflow执行

        Args:
            initial_input: 初始输入数据

        Returns:
            Workflow执行完成后的状态
        """
        if not self._steps:
            raise RuntimeError("Workflow没有定义任何步骤")

        self.logger.info(f"{'='*60}", component="engine")
        self.logger.info(f"Workflow '{self.name}' 开始执行", component="engine")
        self.logger.info(f"步骤数: {len(self._steps)}", component="engine")
        self.logger.info(f"{'='*60}", component="engine")

        self.state.start()
        self._current_step = -1

        # 设置初始输入
        if initial_input is not None:
            self.state.set("initial_input", initial_input)

        try:
            for i, step in enumerate(self._steps):
                self._current_step = i

                # 检查条件
                if step.get("condition") and not step["condition"](self.state):
                    self.logger.info(
                        f"步骤 [{i+1}/{len(self._steps)}] {step['name']} - 条件不满足，跳过",
                        component="engine",
                    )
                    if step.get("agent_name"):
                        self.state.set_agent_state(step["agent_name"], AgentState.SKIPPED)
                    continue

                # 并行步骤
                if step.get("type") == "parallel":
                    self._execute_parallel_step(step, i)
                    continue

                # 普通步骤
                success = self._execute_step(step, i)
                if not success:
                    self.state.complete(success=False)
                    self._print_summary()
                    return self.state

            # 所有步骤完成
            self.state.complete(success=True)
            self.logger.info(f"{'='*60}", component="engine")
            self.logger.info(f"Workflow '{self.name}' 执行成功！", component="engine")
            self._print_summary()

        except Exception as e:
            self.logger.error(f"Workflow执行异常: {e}", component="engine")
            self.state.complete(success=False)
            self._print_summary()
            raise

        return self.state

    def _execute_step(self, step: Dict[str, Any], index: int) -> bool:
        """
        执行单个步骤

        Returns:
            是否成功
        """
        agent_name = step["agent_name"]
        agent = self._agents[agent_name]
        step_num = f"[{index + 1}/{len(self._steps)}]"

        self.logger.info(f"{step_num} 执行步骤: {step['name']}", component="engine")
        self.logger.push_indent()

        # 准备输入
        if step.get("input_mapper"):
            input_data = step["input_mapper"](self.state)
        else:
            # 默认从全局状态获取上一个Agent的输出
            prev_output = self.state.get("last_output")
            input_data = prev_output if prev_output is not None else self.state.get("initial_input")

        self.logger.debug(f"输入类型: {type(input_data).__name__}", component=agent_name)

        # 更新状态
        self.state.set_agent_state(agent_name, AgentState.RUNNING)

        # 执行Agent
        try:
            agent.on_start()
            output = agent.execute(input_data)
            agent.on_end()

            # 记录输出
            self.state.set_agent_output(agent_name, output)
            self.state.set("last_output", output)

            # 输出映射
            if step.get("output_mapper"):
                step["output_mapper"](output, self.state)

            self.state.set_agent_state(agent_name, AgentState.SUCCESS)
            self.logger.info(f"步骤 '{step['name']}' 执行成功", component="engine")

        except Exception as e:
            self.logger.error(f"步骤 '{step['name']}' 执行失败: {e}", component="engine")
            agent.on_error(e)

            # 重试逻辑
            if step.get("retry_count", 0) < self.max_retries:
                step["retry_count"] += 1
                self.logger.info(
                    f"重试 ({step['retry_count']}/{self.max_retries})...",
                    component="engine",
                )
                self.logger.pop_indent()
                return self._execute_step(step, index)

            self.state.set_agent_state(agent_name, AgentState.FAILED)

            if self.error_strategy == "stop":
                self.logger.pop_indent()
                return False
            elif self.error_strategy == "skip":
                self.logger.warning("错误策略: 跳过失败步骤", component="engine")
                self.logger.pop_indent()
                return True

        self.logger.pop_indent()
        return True

    def _execute_parallel_step(self, step: Dict[str, Any], index: int):
        """
        执行并行步骤（简化实现：按顺序执行但逻辑上并行）

        注：真正的并行需要多线程/多进程，这里为了MVP简化为顺序执行，
        但语义上这些步骤之间没有依赖关系，可以并行。
        """
        agent_names = step["agent_names"]
        step_num = f"[{index + 1}/{len(self._steps)}]"

        self.logger.info(f"{step_num} 并行执行: {step['name']}", component="engine")
        self.logger.push_indent()

        for agent_name in agent_names:
            agent = self._agents[agent_name]
            self.logger.info(f"并行Agent: {agent_name}", component="engine")
            self.logger.push_indent()

            try:
                self.state.set_agent_state(agent_name, AgentState.RUNNING)
                agent.on_start()
                output = agent.execute(self.state.get("last_output"))
                agent.on_end()
                self.state.set_agent_output(agent_name, output)
                self.state.set_agent_state(agent_name, AgentState.SUCCESS)
                self.logger.info(f"{agent_name} 完成", component="engine")
            except Exception as e:
                self.logger.error(f"{agent_name} 失败: {e}", component="engine")
                self.state.set_agent_state(agent_name, AgentState.FAILED)
                agent.on_error(e)

            self.logger.pop_indent()

        self.logger.pop_indent()

    def _print_summary(self):
        """打印执行摘要"""
        summary = self.state.summary()
        self.logger.info("", component="engine")
        self.logger.info("--- 执行摘要 ---", component="engine")
        self.logger.info(f"Workflow: {summary['workflow_name']}", component="engine")
        self.logger.info(f"状态: {summary['status']}", component="engine")
        if summary["duration_seconds"]:
            self.logger.info(f"耗时: {summary['duration_seconds']:.2f}s", component="engine")
        self.logger.info(f"Agent状态:", component="engine")
        for agent, state in summary["agent_states"].items():
            self.logger.info(f"  - {agent}: {state}", component="engine")
        self.logger.info(f"{'='*60}", component="engine")

    # --- 重置 ---

    def reset(self):
        """重置Workflow状态，可重新执行"""
        self.state = WorkflowState(self.name)
        self._current_step = -1
        for agent in self._agents.values():
            agent._state = self.state
            agent._inbox.clear()
            self.state.set_agent_state(agent.name, AgentState.IDLE)
        self.logger.clear()
        self.logger.info(f"Workflow '{self.name}' 已重置", component="engine")
