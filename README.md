# Simple Workflow MVP - 代码审查流程

> SE2026课程 Homework 2 项目：基于Agent协作的代码审查Workflow

## 📋 项目简介

本项目实现了一个基于多Agent协作的**代码审查工作流系统**，演示了Workflow编排、Agent间通信、状态管理等核心概念。

### 业务场景

模拟软件开发中的代码审查流程：
```
需求描述 → 代码生成 → 代码审查 → 代码修复 → (可选)二次审查
```

### 三个核心Agent

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| **CodingAgent** | 根据需求生成代码 | 需求描述 | 代码文件 |
| **ReviewAgent** | 审查代码质量 | 代码 | 审查报告（评分、问题列表） |
| **FixAgent** | 自动修复代码问题 | 代码+审查结果 | 修复后的代码 |

## 🏗️ 项目结构

```
.
├── agents/                 # Agent模块
│   ├── __init__.py
│   ├── base.py             # Agent抽象基类
│   ├── coding_agent.py     # 编码Agent
│   ├── review_agent.py     # 审查Agent
│   └── fix_agent.py        # 修复Agent
├── workflow/               # Workflow核心引擎
│   ├── __init__.py
│   ├── message.py          # 消息传递模块
│   ├── state.py            # 状态管理模块
│   ├── logger.py           # 日志追踪模块
│   └── engine.py           # Workflow编排引擎
├── examples/               # 示例脚本
│   ├── __init__.py
│   ├── basic_review.py     # 基础流程示例
│   └── smart_review.py     # 带条件分支的智能流程
├── tests/                  # 单元测试
│   ├── __init__.py
│   └── test_workflow.py    # 综合测试
├── README.md               # 项目说明
└── Design.md               # 设计文档
```

## 🚀 快速开始

### 环境要求

- Python 3.7+
- 无第三方依赖（仅使用Python标准库）

### 运行示例

```bash
# 基础流程示例
python examples/basic_review.py

# 智能审查流程（带条件分支）
python examples/smart_review.py
```

### 运行测试

```bash
python tests/test_workflow.py
```

## 💡 使用方法

### 基础用法

```python
from workflow import WorkflowEngine
from agents import CodingAgent, ReviewAgent, FixAgent

# 1. 创建引擎
engine = WorkflowEngine("MyWorkflow")

# 2. 注册Agent
engine.register_agent(CodingAgent())
engine.register_agent(ReviewAgent())
engine.register_agent(FixAgent())

# 3. 定义流程
engine.add_step("CodingAgent", name="代码生成")
engine.add_step("ReviewAgent", name="代码审查")
engine.add_step("FixAgent", name="代码修复")

# 4. 执行
result = engine.run("实现一个计算器")

# 5. 获取结果
print(result.status)
print(result.get_agent_output("CodingAgent"))
```

### 条件分支

```python
# 只有审查不通过时才执行修复
engine.add_step(
    "FixAgent",
    name="代码修复",
    condition=lambda state: not state.get_agent_output("ReviewAgent", {}).get("passed", True),
)
```

### 输入/输出映射

```python
engine.add_step(
    "ReviewAgent",
    input_mapper=lambda state: state.get_agent_output("CodingAgent"),
    output_mapper=lambda output, state: state.set("review_score", output["score"]),
)
```

## ✨ 核心功能

### 必须实现 ✅

- [x] 至少2个Agent协作完成完整流程
- [x] Agent间消息传递与状态共享
- [x] 基本流程控制（顺序执行）
- [x] MVP可运行

### 推荐实现 ✅

- [x] 条件分支执行
- [x] 循环重试机制
- [x] 并行执行支持
- [x] 执行日志与状态追踪
- [x] 错误处理与恢复机制
- [x] 可扩展的Agent架构

## 📊 评审标准对应

| 维度 | 权重 | 实现情况 |
|------|------|----------|
| 流程完整性 | 40% | ✅ 端到端跑通，支持多种流程组合 |
| Agent协作 | 30% | ✅ 消息传递 + 全局状态共享 + 条件协作 |
| 可扩展性 | 20% | ✅ 插件式Agent注册 + 灵活流程定义 |
| 文档 | 10% | ✅ README + Design.md + 代码注释 |

## 📝 License

课程作业项目
