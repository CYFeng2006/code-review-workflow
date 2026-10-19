"""
Workflow单元测试

测试内容：
1. Message消息模块
2. WorkflowState状态管理
3. WorkflowLogger日志模块
4. BaseAgent基类
5. CodingAgent编码Agent
6. ReviewAgent审查Agent
7. FixAgent修复Agent
8. WorkflowEngine引擎（顺序执行、条件分支、错误处理）
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflow.message import Message, MessageType
from workflow.state import WorkflowState, AgentState, WorkflowStatus
from workflow.logger import WorkflowLogger, LogLevel
from workflow.engine import WorkflowEngine
from agents.base import BaseAgent
from agents.coding_agent import CodingAgent
from agents.review_agent import ReviewAgent
from agents.fix_agent import FixAgent


class TestMessage(unittest.TestCase):
    """测试Message模块"""

    def test_create_message(self):
        msg = Message(
            msg_type=MessageType.TASK,
            sender="AgentA",
            receiver="AgentB",
            content={"data": "test"},
        )
        self.assertEqual(msg.sender, "AgentA")
        self.assertEqual(msg.receiver, "AgentB")
        self.assertEqual(msg.content["data"], "test")
        self.assertIsNotNone(msg.msg_id)
        self.assertIsNotNone(msg.trace_id)

    def test_reply_message(self):
        msg = Message(
            msg_type=MessageType.TASK,
            sender="AgentA",
            receiver="AgentB",
            content={"data": "test"},
        )
        reply = msg.reply(MessageType.RESULT, {"result": "ok"})
        self.assertEqual(reply.sender, "AgentB")
        self.assertEqual(reply.receiver, "AgentA")
        self.assertEqual(reply.trace_id, msg.trace_id)
        self.assertEqual(reply.msg_type, MessageType.RESULT)

    def test_forward_message(self):
        msg = Message(
            msg_type=MessageType.TASK,
            sender="AgentA",
            receiver="AgentB",
            content={"data": "test"},
        )
        forwarded = msg.forward("AgentC", {"extra": "data"})
        self.assertEqual(forwarded.sender, "AgentB")
        self.assertEqual(forwarded.receiver, "AgentC")
        self.assertEqual(forwarded.trace_id, msg.trace_id)
        self.assertEqual(forwarded.content["data"], "test")
        self.assertEqual(forwarded.content["extra"], "data")

    def test_to_dict(self):
        msg = Message(
            msg_type=MessageType.TASK,
            sender="A",
            receiver="B",
            content={"k": "v"},
        )
        d = msg.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["sender"], "A")
        self.assertEqual(d["msg_type"], "task")


class TestWorkflowState(unittest.TestCase):
    """测试Workflow状态管理"""

    def test_initial_state(self):
        state = WorkflowState("test")
        self.assertEqual(state.status, WorkflowStatus.PENDING)
        self.assertIsNotNone(state.created_at)

    def test_start_complete(self):
        state = WorkflowState("test")
        state.start()
        self.assertEqual(state.status, WorkflowStatus.RUNNING)
        self.assertIsNotNone(state.started_at)

        state.complete(success=True)
        self.assertEqual(state.status, WorkflowStatus.COMPLETED)
        self.assertIsNotNone(state.completed_at)

    def test_global_data(self):
        state = WorkflowState("test")
        state.set("key1", "value1")
        self.assertEqual(state.get("key1"), "value1")
        self.assertEqual(state.get("nonexistent", "default"), "default")

    def test_agent_outputs(self):
        state = WorkflowState("test")
        state.set_agent_output("Agent1", {"result": "ok"})
        self.assertEqual(state.get_agent_output("Agent1")["result"], "ok")
        self.assertIsNone(state.get_agent_output("Agent2"))

    def test_agent_states(self):
        state = WorkflowState("test")
        state.set_agent_state("Agent1", AgentState.RUNNING)
        self.assertEqual(state.get_agent_state("Agent1"), AgentState.RUNNING)
        self.assertEqual(state.get_agent_state("Agent2"), AgentState.IDLE)

    def test_summary(self):
        state = WorkflowState("test")
        state.start()
        state.complete(success=True)
        summary = state.summary()
        self.assertEqual(summary["workflow_name"], "test")
        self.assertEqual(summary["status"], "completed")
        self.assertIsNotNone(summary["duration_seconds"])


class TestWorkflowLogger(unittest.TestCase):
    """测试日志模块"""

    def test_log_levels(self):
        logger = WorkflowLogger(level=LogLevel.DEBUG)
        logger.debug("debug msg")
        logger.info("info msg")
        logger.warning("warning msg")
        logger.error("error msg")
        self.assertEqual(len(logger.logs), 4)

    def test_log_level_filter(self):
        logger = WorkflowLogger(level=LogLevel.WARNING)
        logger.debug("debug")
        logger.info("info")
        logger.warning("warning")
        logger.error("error")
        self.assertEqual(len(logger.logs), 2)

    def test_trace_filter(self):
        logger = WorkflowLogger(level=LogLevel.DEBUG)
        logger.info("msg1", trace_id="trace1")
        logger.info("msg2", trace_id="trace2")
        logger.info("msg3", trace_id="trace1")
        self.assertEqual(len(logger.get_logs_by_trace("trace1")), 2)

    def test_indent(self):
        logger = WorkflowLogger(level=LogLevel.INFO, use_color=False)
        logger.push_indent()
        logger.info("indented")
        logger.pop_indent()
        logger.info("not indented")
        self.assertEqual(len(logger.logs), 2)

    def test_summary(self):
        logger = WorkflowLogger(level=LogLevel.DEBUG)
        logger.debug("d")
        logger.info("i")
        logger.warning("w")
        logger.error("e")
        s = logger.summary()
        self.assertEqual(s["debug"], 1)
        self.assertEqual(s["info"], 1)
        self.assertEqual(s["warning"], 1)
        self.assertEqual(s["error"], 1)


class TestCodingAgent(unittest.TestCase):
    """测试编码Agent"""

    def setUp(self):
        self.agent = CodingAgent()
        engine = WorkflowEngine("test")
        engine.register_agent(self.agent)

    def test_execute_with_string(self):
        result = self.agent.execute("实现一个排序算法")
        self.assertIn("code", result)
        self.assertEqual(result["language"], "python")
        self.assertIsInstance(result["code"], str)
        self.assertTrue(len(result["code"]) > 0)

    def test_execute_with_dict(self):
        result = self.agent.execute({
            "requirement": "实现一个计算器",
            "language": "python",
            "filename": "calc.py",
        })
        self.assertIn("code", result)
        self.assertEqual(result["filename"], "calc.py")

    def test_sort_template(self):
        result = self.agent.execute("实现排序功能")
        self.assertIn("def sort_list", result["code"])

    def test_calculator_template(self):
        result = self.agent.execute("实现一个计算器")
        self.assertIn("class Calculator", result["code"])

    def test_todo_template(self):
        result = self.agent.execute("实现待办事项管理")
        self.assertIn("class TodoList", result["code"])

    def test_empty_input(self):
        with self.assertRaises(ValueError):
            self.agent.execute("")

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            self.agent.execute(123)


class TestReviewAgent(unittest.TestCase):
    """测试审查Agent"""

    def setUp(self):
        self.agent = ReviewAgent()
        engine = WorkflowEngine("test")
        engine.register_agent(self.agent)

    def test_review_good_code(self):
        code = '''def hello(name):
    """打招呼函数"""
    return f"Hello, {name}!"


if __name__ == "__main__":
    print(hello("World"))
'''
        result = self.agent.execute({"code": code, "language": "python"})
        self.assertIn("passed", result)
        self.assertIn("score", result)
        self.assertIsInstance(result["score"], int)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    def test_review_code_with_issues(self):
        code = '''def BadFunction(x):
    if x>0:
      return x+1
    else:
        return x-1
'''
        result = self.agent.execute({"code": code, "language": "python"})
        self.assertIn("issues", result)
        self.assertIsInstance(result["issues"], list)
        self.assertGreater(len(result["issues"]), 0)

    def test_review_empty_code(self):
        with self.assertRaises(ValueError):
            self.agent.execute("")

    def test_review_string_input(self):
        result = self.agent.execute("def foo(): pass")
        self.assertIn("passed", result)


class TestFixAgent(unittest.TestCase):
    """测试修复Agent"""

    def setUp(self):
        self.agent = FixAgent()
        engine = WorkflowEngine("test")
        engine.register_agent(self.agent)

    def test_fix_trailing_spaces(self):
        code = "def foo():   \n    pass   \n"
        review_result = {
            "original_code": code,
            "language": "python",
            "issues": [
                {
                    "type": "style",
                    "severity": "info",
                    "message": "有 2 行存在行尾空格",
                }
            ],
        }
        result = self.agent.execute(review_result)
        self.assertIn("fixed_code", result)
        self.assertGreater(result["fix_count"], 0)
        # 验证没有行尾空格
        for line in result["fixed_code"].split("\n"):
            self.assertEqual(line, line.rstrip())

    def test_fix_bare_except(self):
        code = '''try:
    x = 1 / 0
except:
    pass
'''
        review_result = {
            "original_code": code,
            "language": "python",
            "issues": [
                {
                    "type": "error_handling",
                    "severity": "warning",
                    "message": "发现 1 处裸露的 except",
                }
            ],
        }
        result = self.agent.execute(review_result)
        self.assertGreater(result["fix_count"], 0)
        self.assertIn("except Exception:", result["fixed_code"])

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            self.agent.execute(123)


class TestWorkflowEngine(unittest.TestCase):
    """测试Workflow引擎"""

    def test_register_agent(self):
        engine = WorkflowEngine("test")
        agent = CodingAgent()
        engine.register_agent(agent)
        self.assertIn(agent.name, engine.agents)

    def test_register_duplicate_agent(self):
        engine = WorkflowEngine("test")
        engine.register_agent(CodingAgent("Agent1"))
        with self.assertRaises(ValueError):
            engine.register_agent(CodingAgent("Agent1"))

    def test_basic_workflow(self):
        """测试基本顺序执行"""
        engine = WorkflowEngine("test", log_level=LogLevel.WARNING)
        engine.register_agent(CodingAgent("Coder"))
        engine.register_agent(ReviewAgent("Reviewer"))

        engine.add_step("Coder", name="编码")
        engine.add_step("Reviewer", name="审查")

        result = engine.run("实现一个计算器")
        self.assertEqual(result.status, WorkflowStatus.COMPLETED)
        self.assertIsNotNone(result.get_agent_output("Coder"))
        self.assertIsNotNone(result.get_agent_output("Reviewer"))

    def test_conditional_step(self):
        """测试条件分支"""
        engine = WorkflowEngine("test", log_level=LogLevel.WARNING)
        engine.register_agent(CodingAgent("Coder"))
        engine.register_agent(ReviewAgent("Reviewer"))
        engine.register_agent(FixAgent("Fixer"))

        engine.add_step("Coder")
        engine.add_step("Reviewer")
        # FixAgent 应该被执行（因为初始代码通常有问题）
        engine.add_step(
            "Fixer",
            condition=lambda s: not s.get_agent_output("Reviewer", {}).get("passed", True),
        )

        result = engine.run("实现一个排序算法")
        self.assertEqual(result.status, WorkflowStatus.COMPLETED)

    def test_input_output_mapper(self):
        """测试输入输出映射"""
        engine = WorkflowEngine("test", log_level=LogLevel.WARNING)
        engine.register_agent(CodingAgent("Coder"))
        engine.register_agent(ReviewAgent("Reviewer"))

        engine.add_step(
            "Coder",
            input_mapper=lambda s: {"requirement": s.get("initial_input"), "language": "python"},
        )
        engine.add_step(
            "Reviewer",
            input_mapper=lambda s: s.get_agent_output("Coder"),
        )

        result = engine.run("实现一个计算器")
        self.assertEqual(result.status, WorkflowStatus.COMPLETED)

    def test_empty_workflow(self):
        """测试没有步骤的Workflow"""
        engine = WorkflowEngine("test")
        engine.register_agent(CodingAgent())
        with self.assertRaises(RuntimeError):
            engine.run()

    def test_reset(self):
        """测试重置功能"""
        engine = WorkflowEngine("test", log_level=LogLevel.WARNING)
        engine.register_agent(CodingAgent("Coder"))
        engine.add_step("Coder")

        engine.run("test")
        self.assertEqual(engine.state.status, WorkflowStatus.COMPLETED)

        engine.reset()
        self.assertEqual(engine.state.status, WorkflowStatus.PENDING)

    def test_full_review_workflow(self):
        """测试完整的代码审查流程"""
        engine = WorkflowEngine("full_test", log_level=LogLevel.WARNING)
        engine.register_agent(CodingAgent())
        engine.register_agent(ReviewAgent())
        engine.register_agent(FixAgent())

        # 编码 -> 审查 -> 修复
        engine.add_step("CodingAgent", name="编码")
        engine.add_step("ReviewAgent", name="审查")
        engine.add_step("FixAgent", name="修复")

        result = engine.run({
            "requirement": "实现一个待办事项列表",
            "language": "python",
        })

        self.assertEqual(result.status, WorkflowStatus.COMPLETED)

        # 验证各Agent都有输出
        self.assertIsNotNone(result.get_agent_output("CodingAgent"))
        self.assertIsNotNone(result.get_agent_output("ReviewAgent"))
        self.assertIsNotNone(result.get_agent_output("FixAgent"))

        # 验证修复结果
        fix_result = result.get_agent_output("FixAgent")
        self.assertIn("fixed_code", fix_result)
        self.assertIsInstance(fix_result["fixes_applied"], list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
