"""
示例1：基础代码审查流程

演示最基本的 编码 -> 审查 -> 修复 三阶段流程。
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflow import WorkflowEngine, LogLevel
from agents import CodingAgent, ReviewAgent, FixAgent


def main():
    print("\n" + "=" * 70)
    print("  示例1：基础代码审查流程")
    print("  CodingAgent -> ReviewAgent -> FixAgent")
    print("=" * 70 + "\n")

    # 1. 创建Workflow引擎
    engine = WorkflowEngine("CodeReviewWorkflow", log_level=LogLevel.DEBUG)

    # 2. 注册Agent
    engine.register_agent(CodingAgent("CodingAgent"))
    engine.register_agent(ReviewAgent("ReviewAgent"))
    engine.register_agent(FixAgent("FixAgent"))

    # 3. 定义流程（顺序执行）
    engine.add_step(
        agent_name="CodingAgent",
        name="代码生成",
        input_mapper=lambda state: state.get("initial_input"),
    )

    engine.add_step(
        agent_name="ReviewAgent",
        name="代码审查",
        input_mapper=lambda state: state.get_agent_output("CodingAgent"),
    )

    engine.add_step(
        agent_name="FixAgent",
        name="代码修复",
        input_mapper=lambda state: state.get_agent_output("ReviewAgent"),
    )

    # 4. 执行Workflow
    requirement = {
        "requirement": "实现一个待办事项管理工具",
        "language": "python",
        "filename": "todo_list.py",
    }

    result = engine.run(requirement)

    # 5. 输出结果
    print("\n" + "=" * 70)
    print("  执行结果")
    print("=" * 70)

    # 生成的代码
    code_result = result.get_agent_output("CodingAgent")
    if code_result:
        print(f"\n📄 生成的代码 ({code_result['filename']}):")
        print("-" * 70)
        print(code_result["code"])
        print("-" * 70)

    # 审查结果
    review_result = result.get_agent_output("ReviewAgent")
    if review_result:
        print(f"\n🔍 审查结果:")
        print(f"   评分: {review_result['score']}/100")
        print(f"   通过: {'✅ 是' if review_result['passed'] else '❌ 否'}")
        print(f"   问题总数: {review_result['total_issues']}")
        print(f"   严重: {review_result['critical_count']}")
        print(f"   警告: {review_result['warning_count']}")
        print(f"   信息: {review_result['info_count']}")
        if review_result["issues"]:
            print(f"\n   问题详情:")
            for i, issue in enumerate(review_result["issues"][:5], 1):
                emoji = "🔴" if issue["severity"] == "critical" else "🟡" if issue["severity"] == "warning" else "🔵"
                print(f"   {i}. {emoji} [{issue['type']}] {issue['message']}")

    # 修复结果
    fix_result = result.get_agent_output("FixAgent")
    if fix_result:
        print(f"\n🔧 修复结果:")
        print(f"   修复数量: {fix_result['fix_count']}")
        print(f"   剩余问题: {len(fix_result['remaining_issues'])}")
        if fix_result["fixes_applied"]:
            print(f"\n   已应用的修复:")
            for i, fix in enumerate(fix_result["fixes_applied"], 1):
                print(f"   {i}. {fix['fix']}")

        print(f"\n📄 修复后的代码:")
        print("-" * 70)
        print(fix_result["fixed_code"])
        print("-" * 70)

    print(f"\n✅ Workflow执行状态: {result.status.value}")
    summary = result.summary()
    if summary["duration_seconds"]:
        print(f"⏱️  总耗时: {summary['duration_seconds']:.3f}s")

    return result


if __name__ == "__main__":
    main()
