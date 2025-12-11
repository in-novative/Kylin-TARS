# Kylin-TARS GUI Agent

## 📋 项目概述

**openKylin 桌面 GUI Agent** 核心模块，包含：

1. **System-2 推理模板**：任务分解、智能体选择、风险评估
2. **记忆模块**：协作轨迹存储与检索
3. **GUI 操作生成**：基于截图分析生成操作指令

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    用户任务输入                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Master Agent (任务分解层)                       │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  thought_chain:                                         ││
│  │    - task_understanding: 任务理解                       ││
│  │    - task_decomposition: 步骤分解                       ││
│  │    - agent_selection: 智能体选择                        ││
│  │    - risk_assessment: 风险评估                          ││
│  │    - fallback_plan: 回退策略                            ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Sub-Agents (执行层)                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │FileAgent │ │Settings  │ │AppAgent  │ │Browser   │       │
│  │文件操作  │ │Agent     │ │应用操作  │ │Agent     │       │
│  │          │ │系统设置  │ │          │ │浏览器    │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              GUI Action (操作层)                             │
│  click | type | hotkey | scroll | drag | wait | finished   │
└─────────────────────────────────────────────────────────────┘
```

## 📁 文件结构

```
/data1/cyx/Kylin-TARS/
├── system2_prompt.py          # System-2 推理模板（Day2）
├── memory_store.py            # 记忆模块：轨迹存储（Day3）
├── system2_memory.py          # 推理+记忆整合（Day4）
├── memory_retrieve.py         # 高效检索与复用（Day5）
├── mcp_integration.py         # MCP 联调模块（Day6）
├── full_integration.py        # 全链路联调脚本（Day6）
├── mcp_config.py              # MCP统一配置
├── agent_adapter.py           # 子智能体适配器
├── start_integration.sh       # 联调启动脚本
├── test_uitars_api.py         # 模型API测试（Day1）
├── requirements_system2.txt   # 依赖列表
├── README_System2.md          # 本文档
│
├── mcp_system/                # 成员A：MCP Server（D-Bus服务）
│   ├── mcp_server/
│   │   ├── mcp_server.py        # 原始版本（有语法错误）
│   │   ├── mcp_server_fixed.py  # 修复版本
│   │   └── test_mcp_server.py
│   └── mcp_client/
│       ├── mcp_client.py
│       └── agent_registry.py
│
└── Desktop/agent_project/     # 成员C：子智能体实现
    ├── src/
    │   ├── file_agent_logic.py      # FileAgent 核心逻辑
    │   ├── file_agent_mcp.py        # FileAgent D-Bus服务
    │   ├── settings_agent_logic.py  # SettingsAgent 核心逻辑
    │   ├── settings_agent_mcp.py    # SettingsAgent D-Bus服务
    │   └── gradio_ui.py             # Gradio 可视化界面
    └── README.md
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 激活环境
conda activate uitars-vllm

# 安装额外依赖
pip install json5>=0.9.22
```

### 2. 启动 vLLM 服务

```bash
python -m vllm.entrypoints.openai.api_server \
    --model /data1/models/UI-TARS-1.5-7B \
    --trust-remote-code \
    --dtype bfloat16 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.7 \
    --port 8000
```

### 3. 运行测试

```bash
cd /data1/cyx/anything
python system2_prompt.py
```

## 📖 API 使用说明

### 生成 Master 推理链

```python
from system2_prompt import generate_master_reasoning

# 生成任务分解推理链
reasoning = generate_master_reasoning(
    user_task="搜索下载目录的png文件并设置为壁纸",
    max_retries=3,
    verbose=True
)

print(reasoning["thought_chain"]["task_decomposition"])
print(reasoning["thought_chain"]["agent_selection"])
```

### 生成 GUI 操作

```python
from system2_prompt import generate_gui_action

# 基于截图生成GUI操作
action = generate_gui_action(
    instruction="点击搜索按钮",
    screenshot_path="/path/to/screenshot.png",
    verbose=True
)

print(action["action"])  # {"type": "click", "params": {"start_box": "(100,200)"}}
```

### 完整推理流程

```python
from system2_prompt import execute_reasoning_pipeline

# 执行完整推理流程
result = execute_reasoning_pipeline(
    user_task="把系统音量调到50%",
    screenshot_path="/path/to/screenshot.png",
    verbose=True
)

# 获取结果
print(result["master_reasoning"])  # 任务分解
print(result["gui_action"])        # GUI操作
print(result["success"])           # 是否成功
```

## 📤 输出格式

### Master 推理链格式

```json
{
    "thought_chain": {
        "task_understanding": "对用户任务的理解",
        "task_decomposition": "1. 步骤一；2. 步骤二；3. 步骤三",
        "agent_selection": [
            {"step": 1, "agent": "FileAgent", "reason": "需要文件搜索功能"},
            {"step": 2, "agent": "SettingsAgent", "reason": "需要系统设置功能"}
        ],
        "risk_assessment": "核心风险描述",
        "fallback_plan": "风险回退方案"
    },
    "execution_plan": [
        {"step": 1, "action": "具体操作", "agent": "FileAgent"},
        {"step": 2, "action": "具体操作", "agent": "SettingsAgent"}
    ],
    "milestone_markers": ["search_complete", "setting_applied", "verified"]
}
```

### GUI 操作格式

```json
{
    "thought_chain": {
        "current_state": "当前界面状态",
        "reasoning": "操作理由"
    },
    "action": {
        "type": "click",
        "params": {
            "start_box": "(100,200)"
        }
    },
    "confidence": 0.95,
    "milestone": "step_1_complete"
}
```

## 🔧 Action Space（操作空间）

| 操作 | 格式 | 说明 |
|------|------|------|
| click | `click(start_box='(x,y)')` | 单击 |
| left_double | `left_double(start_box='(x,y)')` | 双击 |
| right_single | `right_single(start_box='(x,y)')` | 右键单击 |
| drag | `drag(start_box='(x1,y1)', end_box='(x2,y2)')` | 拖拽 |
| hotkey | `hotkey(key='ctrl c')` | 快捷键 |
| type | `type(content='文本')` | 输入文本 |
| scroll | `scroll(start_box='(x,y)', direction='down')` | 滚动 |
| wait | `wait()` | 等待5秒 |
| finished | `finished(content='完成描述')` | 任务完成 |

## 💾 记忆模块 (memory_store.py)

### 存储轨迹
```python
from memory_store import save_collaboration_trajectory

save_collaboration_trajectory(
    task="搜索png文件并设置为壁纸",
    reasoning_chain=reasoning,  # 推理链字典
    execution_result="壁纸设置成功",
    screenshot_paths=["./screenshot.png"],
    success=True
)
```

### 检索轨迹
```python
from memory_store import list_trajectories, search_trajectories, find_similar_task

# 列出最近轨迹
recent = list_trajectories(limit=10)

# 关键词搜索
results = search_trajectories(keyword="壁纸")

# 查找相似任务（用于推理链复用）
similar = find_similar_task("搜索jpg文件设为壁纸", threshold=0.5)
```

### 与 System-2 集成
```python
from system2_prompt import execute_reasoning_pipeline
from memory_store import save_from_reasoning_result

result = execute_reasoning_pipeline(user_task="调整音量到50%")
save_from_reasoning_result(result, execution_result="音量已调整")
```

## 🔗 推理+记忆整合 (system2_memory.py)

### 一站式推理+存储
```python
from system2_memory import reasoning_with_memory

# 自动完成：推理链复用检查 → 生成推理链 → MCP格式校验 → 存储
reasoning_chain, trajectory_path = reasoning_with_memory(
    user_task="搜索png文件设为壁纸",
    screenshot_path="./screenshot.png",  # 可选
    enable_reuse=True,  # 启用推理链复用
    verbose=True
)
```

### Master Agent 调用接口
```python
from system2_memory import get_reasoning_for_master, get_next_action_for_master

# 获取推理链（MCP格式）
reasoning = get_reasoning_for_master(user_task="调整音量到50%")

# 获取下一步GUI操作
action = get_next_action_for_master(
    user_task="点击音量控制",
    screenshot_path="./current.png"
)
```

### 更新执行结果
```python
from system2_memory import update_trajectory_result

# 子智能体执行完成后更新轨迹
update_trajectory_result(
    task_hash="a1b2c3d4",
    execution_result="音量已调整到50%",
    success=True,
    screenshot_paths=["./result.png"]
)
```

## 🔍 高效检索 (memory_retrieve.py)

### 模糊匹配检索
```python
from memory_retrieve import retrieve_similar_trajectory, reuse_reasoning_chain

# 检索相似轨迹
similar = retrieve_similar_trajectory(
    user_task="把下载文件夹的png图片移到垃圾桶",
    threshold=70,  # 相似度阈值 0-100
    verbose=True
)

# 直接复用推理链
reasoning = reuse_reasoning_chain(user_task, threshold=70)
```

### 检索优先流程
```python
from memory_retrieve import reasoning_with_retrieval

# 自动检索复用，无匹配则生成新推理链
reasoning, status = reasoning_with_retrieval(
    user_task="搜索jpg文件设为壁纸",
    threshold=60
)
# status: "reused" / "generated" / "fallback"
```

## 🔌 MCP 联调 (mcp_integration.py)

### 连接 MCP Server
```python
from mcp_integration import MCPClient

client = MCPClient(bus_type="session")
client.connect()

# 健康检查
if client.ping():
    print("MCP Server 正常运行")
```

### MCP 集成推理
```python
from mcp_integration import mcp_reasoning, mcp_status

# 一站式流程：推理 → MCP工具调用 → 存储轨迹
reasoning, results = mcp_reasoning(user_task="搜索png文件设为壁纸")

# 查看 MCP 状态
print(mcp_status())
```

### 直接调用 MCP 工具
```python
from mcp_integration import mcp_tool_call

result = mcp_tool_call("search_file", {
    "dir": "~/Downloads",
    "pattern": "*.png"
})
```

## ✅ 验收标准

**System-2 推理模板**
- [x] 5个测试任务中至少4个能生成格式正确的JSON推理链
- [x] 格式错误时能自动重试，最终返回兜底推理链
- [x] 推理链中的智能体选择合理

**记忆模块**
- [x] 存储目录自动创建（~/.config/kylin-gui-agent/collaboration_memory）
- [x] 轨迹文件命名格式：unix时间戳_任务哈希.json
- [x] 支持关键词/智能体检索
- [x] 支持相似任务查找（推理链复用）

**推理+记忆整合**
- [x] 推理链生成后自动存储到记忆
- [x] 相似任务自动复用历史推理链
- [x] MCP 格式校验和标准化
- [x] Master Agent 标准化调用接口

**高效检索 (Day5)**
- [x] 模糊匹配检索（fuzzywuzzy）
- [x] 综合相似度算法（文本+关键词）
- [x] 检索优先推理流程
- [x] 检索耗时 < 1秒

**MCP 联调 (Day6)**
- [x] D-Bus 连接与健康检查
- [x] 推理链适配 ToolsList
- [x] 推理链驱动 ToolsCall
- [x] MCP 结果存入记忆
- [x] 模拟模式支持（无需真实 MCP Server）

## 🐛 常见问题

### Q: JSON解析失败怎么办？
A: 脚本已内置容错机制：
1. 使用 `json5` 库进行容错解析
2. 自动移除末尾多余逗号
3. 支持自动重试（默认3次）
4. 最终使用兜底推理链

### Q: 如何调整推理链格式？
A: 修改 `system2_prompt.py` 中的 `SYSTEM2_MASTER_PROMPT` 模板。

### Q: 如何集成到现有系统？
A: 导入并调用核心函数即可：
```python
from system2_prompt import generate_master_reasoning, generate_gui_action
```

## 🔗 全链路联调

### 联调架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         用户任务输入                                 │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 1: 记忆检索 (memory_retrieve.py)                              │
│          └─→ 找到相似轨迹？ → 复用历史推理链                         │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 2: System-2 推理 (system2_memory.py)                          │
│          └─→ 任务分解 + 智能体选择 + 风险评估                        │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 3: MCP 工具调用 (mcp_integration.py)                          │
│          ├─→ FileAgent.search_file                                  │
│          ├─→ FileAgent.move_to_trash                                │
│          ├─→ SettingsAgent.change_wallpaper                         │
│          └─→ SettingsAgent.adjust_volume                            │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 4: 协作轨迹存储 (memory_store.py)                             │
│          └─→ 任务 + 推理链 + 执行结果 + 截图                         │
└─────────────────────────────────────────────────────────────────────┘
```

### 快速联调

```bash
# 模拟模式（无需D-Bus，推荐用于开发测试）
cd /data1/cyx/Kylin-TARS
python full_integration.py

# 完整模式（需要D-Bus环境）
./start_integration.sh
```

### 联调命令（完整模式）

```bash
# 终端1：启动 MCP Server（成员A）
dbus-run-session -- python mcp_system/mcp_server/mcp_server_fixed.py

# 终端2：注册子智能体
python agent_adapter.py

# 终端3：运行全链路测试
python full_integration.py

# 或使用 Gradio 界面（成员C）
cd Desktop/agent_project && python src/gradio_ui.py
```

### D-Bus 服务配置

| 组件 | 服务名 | 说明 |
|------|--------|------|
| MCP Server | `com.kylin.ai.mcp.MasterAgent` | 成员A |
| FileAgent | `com.mcp.agent.file` | 成员C |
| SettingsAgent | `com.mcp.agent.settings` | 成员C |

### 已知问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| D-Bus服务名不一致 | 成员A/C使用不同配置 | 使用 `agent_adapter.py` 适配 |
| MCP Server语法错误 | 第112、134行三元运算符语法 | 使用 `mcp_server_fixed.py` |
| 子智能体注册失败 | 字段名不一致(name/agent_name) | 修复版支持两种字段名 |

## 📝 更新日志

- **v1.5** (2024-12): 全链路联调
  - 全链路联调脚本 (`full_integration.py`)
  - MCP配置统一 (`mcp_config.py`)
  - 子智能体适配器 (`agent_adapter.py`)
  - 修复成员A MCP Server语法错误
  - D-Bus服务名适配方案

- **v1.4** (2024-12): MCP 联调模块
  - D-Bus 连接管理（MCPClient）
  - 适配 MCP 10 个标准接口
  - 推理链驱动 ToolsCall 调用
  - 支持模拟模式（无需真实 MCP Server）

- **v1.3** (2024-12): 高效检索模块
  - 基于 fuzzywuzzy 的模糊匹配
  - 综合相似度算法
  - 检索优先推理流程

- **v1.2** (2024-12): 推理+记忆整合
  - 一站式推理+存储流程
  - MCP 格式校验和标准化

- **v1.1** (2024-12): 记忆模块
  - 协作轨迹存储与检索

- **v1.0** (2024-12): 初始版本
  - Master推理链生成
  - GUI操作生成

