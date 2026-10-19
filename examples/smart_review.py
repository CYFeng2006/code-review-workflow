"""
示例2：带条件分支的代码审查流程

演示高级功能：
- 条件分支：审查通过则结束，不通过则修复
- 循环重试：修复后重新审查，直到通过或达到最大轮次
- 状态共享：通过全局状态传递数据
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflow import WorkflowEngine, LogLevel
from agents import CodingAgent, ReviewAgent, FixAgent


def create_smart_review_workflow(max_rounds: int = 3) -> WorkflowEngine:
    """
    创建智能代码审查Workflow

    流程：
    1. 编码 (CodingAgent)
    2. 审查 (ReviewAgent)
    3. 判断：通过? -> 结束；不通过? -> 修复
    4. 修复 (FixAgent)
    5. 重新审查 (ReviewAgent)
    6. 循环直到通过或达到最大轮次

    Args:
        max_rounds: 最大修复轮次

    Returns:
        WorkflowEngine实例
    """
    engine = WorkflowEngine("SmartReviewWorkflow", log_level=LogLevel.DEBUG)

    # 注册Agent
    engine.register_agent(CodingAgent("CodingAgent"))
    engine.register_agent(ReviewAgent("ReviewAgent"))
    engine.register_agent(FixAgent("FixAgent"))

    # 设置最大重试次数
    engine.max_retries = max_rounds
    engine.error_strategy = "stop"

    # 步骤1：代码生成
    engine.add_step(
        agent_name="CodingAgent",
        name="1. 代码生成",
        input_mapper=lambda state: state.get("initial_input"),
    )

    # 步骤2：首次审查
    engine.add_step(
        agent_name="ReviewAgent",
        name="2. 首次代码审查",
        input_mapper=lambda state: state.get_agent_output("CodingAgent"),
    )

    # 步骤3：条件修复 - 只有审查不通过才执行
    engine.add_step(
        agent_name="FixAgent",
        name="3. 代码修复",
        condition=lambda state: not state.get_agent_output("ReviewAgent", {}).get("passed", True),
        input_mapper=lambda state: state.get_agent_output("ReviewAgent"),
    )

    # 步骤4：二次审查 - 只有执行了修复才执行
    engine.add_step(
        agent_name="ReviewAgent",
        name="4. 修复后审查",
        condition=lambda state: state.get_agent_output("FixAgent") is not None,
        input_mapper=lambda state: {
            "code": state.get_agent_output("FixAgent", {}).get("fixed_code", ""),
            "language": state.get_agent_output("FixAgent", {}).get("language", "python"),
            "filename": state.get_agent_output("FixAgent", {}).get("filename", "fixed.py"),
        },
    )

    return engine


def main():
    print("\n" + "=" * 70)
    print("  示例2：带条件分支的智能代码审查流程")
    print("  编码 -> 审查 -> (条件)修复 -> (条件)二次审查")
    print("=" * 70 + "\n")

    # 创建Workflow
    engine = create_smart_review_workflow(max_rounds=3)

    # 执行
    requirement = {
        "requirement": "实现一个冒泡排序算法",
        "language": "python",
        "filename": "bubble_sort.py",
    }

    result = engine.run(requirement)

    # 输出结果
    print("\n" + "=" * 70)
    print("  执行结果")
    print("=" * 70)

    # 各步骤状态
    print("\n📊 步骤执行状态:")
    agent_states = result.agent_states
    for agent, state in agent_states.items():
        status_icon = {
            "success": "✅",
            "failed": "❌",
            "skipped": "⏭️",
            "running": "🔄",
            "idle": "⏸️",
        }.get(state.value, "❓")
        print(f"   {status_icon} {agent}: {state.value}")

    # 最终代码
    fix_output = result.get_agent_output("FixAgent")
    if fix_output:
        final_code = fix_output["fixed_code"]
        source = "修复后代码"
    else:
        code_output = result.get_agent_output("CodingAgent")
        final_code = code_output["code"] if code_output else ""
        source = "原始代码"

    print(f"\n📄 最终代码 ({source}):")
    print("-" * 70)
    print(final_code)
    print("-" * 70)

    # 最终审查结果
    final_review = result.get_agent_output("ReviewAgent")
    if final_review:
        print(f"\n🔍 最终审查结果:")
        print(f"   评分: {final_review['score']}/100")
        print(f"   通过: {'✅ 是' if final_review['passed'] else '❌ 否'}")

    print(f"\n✅ Workflow执行状态: {result.status.value}")
    summary = result.summary()
    if summary["duration_seconds"]:
        print(f"⏱️  总耗时: {summary['duration_seconds']:.3f}s")

    return result


if __name__ == "__main__":
    main()
