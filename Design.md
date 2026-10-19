# 设计文档 - Simple Workflow MVP

## 1. 系统架构

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      WorkflowEngine                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  步骤1   │→│  步骤2   │→│  步骤3   │→│  ...     │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   WorkflowState                      │   │
│  │  全局数据  +  Agent输出  +  Agent状态  +  执行历史    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   WorkflowLogger                     │   │
│  │    分级日志  +  trace追踪  +  执行摘要                 │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
          │              │              │
          ▼              ▼              ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ Agent A │    │ Agent B │    │ Agent C │
    └─────────┘    └─────────┘    └─────────┘
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                   ┌──────────┐
                   │  Message │  消息传递
                   └──────────┘
```

### 1.2 核心模块职责

| 模块 | 职责 | 关键类/函数 |
|------|------|------------|
| **engine** | Workflow编排核心，管理Agent注册、流程定义、执行控制 | `WorkflowEngine` |
| **message** | Agent间消息传递的结构定义 | `Message`, `MessageType` |
| **state** | 全局状态管理，数据共享 | `WorkflowState`, `AgentState` |
| **logger** | 执行日志与状态追踪 | `WorkflowLogger`, `LogLevel` |
| **agents/base** | Agent抽象基类，定义Agent生命周期 | `BaseAgent` |

## 2. 核心设计

### 2.1 Agent设计

#### BaseAgent 抽象基类

所有Agent继承自 `BaseAgent`，定义了统一的生命周期和能力接口：

```python
class BaseAgent(ABC):
    # 生命周期钩子
    def on_start(self)      # 执行前
    def on_end(self)        # 执行后
    def on_error(self, e)   # 出错时

    # 核心方法（子类必须实现）
    @abstractmethod
    def execute(self, input_data) -> Any

    # 消息通信
    def send_message(receiver, content)
    def receive_message(message)
    def reply_to(original_msg, content)

    # 状态访问
    def set_state_data(key, value)
    def get_state_data(key, default)
```

**设计要点：**
- 统一的生命周期钩子，便于扩展
- 消息收发能力，支持Agent间直接通信
- 通过全局状态实现数据共享
- 每个Agent有独立的日志记录器

### 2.2 消息传递设计

```
┌─────────────────────────────────────────┐
│              Message                     │
├─────────────────────────────────────────┤
│  msg_id:      消息唯一标识               │
│  msg_type:    消息类型 (task/result/...) │
│  sender:      发送者名称                 │
│  receiver:    接收者名称                 │
│  content:     消息内容 (字典)            │
│  timestamp:   时间戳                     │
│  metadata:    元数据 (trace_id等)        │
└─────────────────────────────────────────┘
```

**消息类型：**
- `TASK` - 任务输入
- `RESULT` - 执行结果
- `ERROR` - 错误信息
- `STATUS` - 状态更新
- `CONTROL` - 控制信号

**核心操作：**
- `reply()` - 基于当前消息创建回复（保持trace_id）
- `forward()` - 转发消息给新接收者

### 2.3 状态管理设计

`WorkflowState` 提供三层状态管理：

```
WorkflowState
├── 全局数据 (global_data)
│   └── 所有Agent共享的键值对存储
├── Agent输出 (agent_outputs)
│   └── 每个Agent的执行结果
├── Agent状态 (agent_states)
│   └── idle/running/success/failed/skipped
└── 执行历史 (history)
    └── 所有状态变更的时间线记录
```

**状态枚举：**

Agent状态：
- `IDLE` - 空闲
- `RUNNING` - 运行中
- `SUCCESS` - 成功
- `FAILED` - 失败
- `SKIPPED` - 跳过

Workflow状态：
- `PENDING` - 待执行
- `RUNNING` - 运行中
- `COMPLETED` - 成功完成
- `FAILED` - 失败
- `CANCELLED` - 取消

### 2.4 Workflow引擎设计

#### 执行模型

Workflow引擎采用**顺序执行**模型，按步骤定义的顺序依次执行：

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│  Step 1 │────▶│  Step 2 │────▶│  Step 3 │
└─────────┘     └─────────┘     └─────────┘
     │               │               │
     ▼               ▼               ▼
  Agent A         Agent B         Agent C
```

#### 步骤定义

每个步骤包含以下配置：

```python
{
    "name": "步骤名称",
    "agent_name": "执行的Agent",
    "input_mapper": func,     # 输入映射函数
    "output_mapper": func,    # 输出映射函数
    "condition": func,        # 条件判断函数
    "retry_count": 0,         # 已重试次数
}
```

#### 条件分支

通过 `condition` 参数实现条件分支：

```
         ┌──────────────┐
         │  代码审查     │
         └──────┬───────┘
                │
        ┌───────▼───────┐
        │  审查通过？    │
        └───┬────────┬───┘
            │ 是     │ 否
            ▼        ▼
        ┌───────┐ ┌───────┐
        │  结束  │ │ 修复  │
        └───────┘ └───┬───┘
                      │
                      ▼
                ┌──────────┐
                │ 二次审查  │
                └──────────┘
```

#### 错误处理策略

- `stop` - 遇到错误立即停止（默认）
- `skip` - 跳过失败步骤继续执行
- `retry` - 自动重试（最多N次）

## 3. 代码审查流程设计

### 3.1 业务流程

```
┌─────────────┐
│  需求输入    │
└──────┬──────┘
       ▼
┌─────────────┐     CodingAgent
│  代码生成    │     根据需求生成代码
└──────┬──────┘
       ▼
┌─────────────┐     ReviewAgent
│  代码审查    │     语法/规范/复杂度检查
└──────┬──────┘
       │
       ├─ 通过 ──────────► 结束
       │
       └─ 不通过 ──► ┌─────────────┐   FixAgent
                     │  代码修复    │   自动修复可修复问题
                     └──────┬──────┘
                            ▼
                     ┌─────────────┐   ReviewAgent
                     │  二次审查    │   验证修复效果
                     └──────┬──────┘
                            ▼
                          结束
```

### 3.2 CodingAgent 实现

**功能：** 根据需求描述生成代码模板

**生成策略：** 基于关键词匹配的模板生成
- 检测到"排序" → 生成冒泡排序实现
- 检测到"计算器" → 生成计算器类
- 检测到"待办" → 生成待办事项管理
- 其他 → 生成通用函数模板

**输入格式：**
```python
{
    "requirement": "需求描述",
    "language": "python",     # 可选
    "filename": "output.py",  # 可选
}
```

**输出格式：**
```python
{
    "code": "...",              # 生成的代码
    "language": "python",
    "filename": "output.py",
    "requirement": "原始需求",
    "description": "功能描述",
    "lines_of_code": 30,
}
```

### 3.3 ReviewAgent 实现

**功能：** 对代码进行多维度质量审查

**检查项：**

| 检查类型 | 严重程度 | 检查内容 |
|---------|---------|---------|
| 语法检查 | critical/warning | 括号匹配、语法错误 |
| 命名规范 | warning/info | 类名大驼峰、函数名蛇形 |
| 注释检查 | info | 文档字符串、注释比例 |
| 错误处理 | warning/info | 裸露except、除零保护 |
| 复杂度 | warning | 函数长度、嵌套深度 |
| 代码风格 | info | 行长度、行尾空格、TODO |

**评分算法：**
- 基础分 100
- 每个 critical 问题 -20
- 每个 warning 问题 -5
- 每个 info 问题 -2
- 最终分数范围 [0, 100]

**通过条件：** 分数 >= 60 且无 critical 问题

### 3.4 FixAgent 实现

**功能：** 根据审查结果自动修复代码问题

**可修复的问题类型：**

| 问题类型 | 修复策略 |
|---------|---------|
| 行尾空格 | 删除所有行尾空格 |
| 裸露except | 改为 `except Exception:` |
| 类名不规范 | 首字母大写 |
| 缺少文档字符串 | 添加docstring模板 |
| 未闭合括号 | 补充缺失的闭合括号 |
| Python2风格print | 改为函数调用 |

**设计原则：**
- 只修复确定安全的问题
- 复杂问题留给人工处理
- 记录每个修复的详情

## 4. 可扩展性设计

### 4.1 新增Agent

只需继承 `BaseAgent` 并实现 `execute()` 方法：

```python
class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__("MyAgent", "自定义Agent")

    def execute(self, input_data):
        # 自定义逻辑
        return result
```

然后注册到Workflow引擎即可使用。

### 4.2 新增流程

通过链式调用灵活定义流程：

```python
engine = WorkflowEngine("MyFlow")
engine.register_agent(AgentA())
engine.register_agent(AgentB())
engine.register_agent(AgentC())

engine.add_step("AgentA")
engine.add_step("AgentB", condition=lambda s: ...)
engine.add_step("AgentC")
```

### 4.3 扩展检查项（ReviewAgent）

在 `ReviewAgent.checks` 列表中添加新的检查方法即可。

### 4.4 扩展修复能力（FixAgent）

在 `FixAgent._apply_fix()` 中添加新的问题类型处理。

## 5. 技术选型

| 技术 | 选择 | 原因 |
|------|------|------|
| 语言 | Python | 简洁、生态丰富、适合AI/Agent项目 |
| 依赖 | 仅标准库 | 降低部署门槛，MVP阶段足够 |
| 架构 | 插件式 | 灵活扩展Agent和流程 |
| 通信 | 消息+共享状态 | 兼顾灵活性和简洁性 |

## 6. 未来优化方向

1. **真正的并行执行** - 引入多线程/多进程
2. **可视化编排界面** - Web端拖拽式流程设计
3. **持久化支持** - 执行状态持久化到数据库
4. **分布式部署** - Agent可部署在不同节点
5. **LLM集成** - 接入大模型增强Agent能力
6. **更多Agent类型** - 测试Agent、文档Agent等
