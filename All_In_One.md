# KYLIN-TARS 项目全貌文档

## 📋 项目概述

**KYLIN-TARS** 是一个基于 **openKylin（麒麟）操作系统**的智能Agent管理系统，采用多智能体协作架构，通过统一的Web界面实现对桌面系统的智能操作和管理。

### 核心定位

KYLIN-TARS 旨在构建一个**智能化的桌面操作系统助手**，能够理解用户的自然语言指令，自动规划任务执行步骤，调用相应的专业智能体完成具体操作，并具备记忆学习能力，不断提升用户体验。

---

## 🏗️ 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      Web UI (Gradio)                        │
│                  http://localhost:7870                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   主Agent (Master Agent)                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  任务规划模块 (System-2 推理)                         │  │
│  │  • 任务理解与分解                                      │  │
│  │  • 智能体选择                                          │  │
│  │  • 风险评估与回退策略                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  记忆存储模块                                          │  │
│  │  • 协作轨迹存储                                        │  │
│  │  • 语义检索与复用                                      │  │
│  │  • 用户偏好学习                                        │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    MCP 管理系统                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  MCP Server (D-Bus 服务)                              │  │
│  │  • 子智能体注册与管理                                  │  │
│  │  • 工具调用路由                                        │  │
│  │  • 负载均衡与故障转移                                  │  │
│  │  • 状态监控与广播                                      │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ FileAgent   │ │SettingsAgent│ │NetworkAgent │ │  AppAgent   │
│ 文件管理    │ │ 系统设置    │ │ 网络管理    │ │  应用管理   │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
        │              │              │              │
        └──────────────┼──────────────┼──────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐
│MonitorAgent │ │ MediaAgent  │
│ 系统监控    │ │  媒体控制   │
└─────────────┘ └─────────────┘
```

### 三层架构说明

#### 1. **展示层（Web UI）**
- **技术栈**: Gradio
- **功能**: 提供统一的Web界面，支持任务执行、各智能体功能操作、记忆轨迹查询、协作日志查看等
- **访问地址**: `http://localhost:7870`

#### 2. **决策层（主Agent）**
- **核心职责**:
  - **任务规划**: 理解用户指令，拆解为可执行的子任务
  - **任务拆解**: 将复杂任务分解为2-5个步骤，每个步骤对应单个工具调用
  - **记忆存储**: 存储任务执行轨迹，支持相似任务检索与复用
- **技术实现**: System-2 推理引擎 + 记忆存储模块

#### 3. **执行层（MCP + 子智能体）**
- **MCP系统**: 
  - 负责子智能体的注册、发现、调用
  - 提供统一的工具调用接口
  - 实现负载均衡和故障转移
- **6大子智能体**: 各自负责特定领域的操作

---

## 🤖 核心组件详解

### 一、主Agent (Master Agent)

主Agent是整个系统的"大脑"，负责高级决策和协调。

#### 1.1 任务规划模块（System-2 推理）

**位置**: `run/system2_prompt.py`, `memory/system2_memory.py`

**核心功能**:

1. **任务理解**
   - 解析用户的自然语言指令
   - 识别任务类型和所需资源
   - 理解上下文依赖关系

2. **任务分解**
   - 将复杂任务拆分为2-5个可执行步骤
   - 每个步骤对应单个工具调用
   - 支持步骤间的上下文关联（`context_ref`字段）

3. **智能体选择**
   - 根据子任务类型选择最合适的智能体
   - 考虑智能体的能力和当前状态
   - 提供选择理由

4. **风险评估**
   - 识别可能的执行风险
   - 制定回退策略

**推理链格式**:

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
        {
            "step": 1,
            "action": "具体操作描述",
            "agent": "FileAgent",
            "tool": "file_agent.search_file",
            "context_ref": null,
            "tool_extend": false
        }
    ],
    "milestone_markers": ["milestone_1", "milestone_2"]
}
```

**关键文件**:
- `run/system2_prompt.py`: System-2 Prompt模板和推理函数
- `memory/system2_memory.py`: 推理与记忆整合模块
- `run/instruction_completer.py`: 指令补全/追问模块

#### 1.2 记忆存储模块

**位置**: `memory/`

**核心功能**:

1. **协作轨迹存储** (`memory_store.py`)
   - 存储任务、推理链、执行结果、截图路径
   - 支持时间戳和元数据记录
   - 自动生成任务哈希标识

2. **语义检索** (`memory_retrieve.py`)
   - 基于语义相似度检索历史任务
   - 支持推理链复用
   - 计算综合相似度（任务描述 + 执行结果）

3. **用户偏好学习**
   - 记录用户的操作习惯
   - 在推理链生成时注入用户偏好
   - 支持偏好可视化

**存储结构**:
```
~/.config/kylin-gui-agent/
├── collaboration_memory/     # 协作轨迹存储目录
│   ├── trajectory_20241217_*.json
│   └── ...
└── user_preference.json      # 用户偏好文件
```

**关键文件**:
- `memory/memory_store.py`: 轨迹存储
- `memory/memory_retrieve.py`: 高级检索功能
- `memory/memory_visualization.py`: 记忆可视化

---

### 二、MCP 管理系统

MCP (Master Control Protocol) 是子智能体的统一管理协议。

#### 2.1 MCP Server

**位置**: `mcp_system/mcp_server/mcp_server.py`

**核心功能**:

1. **子智能体注册**
   - 接收子智能体的注册请求
   - 存储智能体的D-Bus服务信息
   - 支持多实例智能体（同一智能体的多个实例）

2. **工具管理**
   - 维护所有可用工具的注册表
   - 提供工具列表查询接口
   - 支持工具调用路由

3. **负载均衡**
   - 监控智能体状态（online/busy/offline/error）
   - 根据CPU占用选择最优实例
   - 自动故障转移

4. **状态监控**
   - 心跳检测
   - 状态广播
   - 健康检查

**D-Bus接口**:
- `AgentRegister`: 注册子智能体
- `AgentUnregister`: 注销子智能体
- `AgentsList`: 获取智能体列表
- `ToolsList`: 获取工具列表
- `ToolsCall`: 调用工具
- `Ping`: 健康检查

**关键文件**:
- `mcp_system/mcp_server/mcp_server.py`: MCP Server实现
- `run/mcp_integration.py`: MCP客户端封装
- `run/mcp_config.py`: MCP配置管理

#### 2.2 MCP Client

**位置**: `mcp_system/mcp_client/`

**功能**: 封装与MCP Server的D-Bus通信，提供便捷的调用接口。

---

### 三、6大子智能体

#### 3.1 FileAgent（文件管理智能体）

**位置**: `desktop/agent_project/src/file_agent_logic.py`, `file_agent_mcp.py`

**核心功能**:

1. **文件搜索** (`search_file`)
   - 按关键词搜索指定目录
   - 支持递归/非递归搜索
   - 返回文件列表和统计信息

2. **文件操作** (`move_to_trash`)
   - 将文件/目录移动到回收站
   - 支持批量操作

3. **批量重命名** (`batch_rename`)
   - 支持4种重命名规则：
     - `prefix_seq`: 前缀+序号
     - `date_prefix_seq`: 日期前缀+序号
     - `suffix_seq`: 后缀+序号
     - `date_suffix_seq`: 日期后缀+序号
   - 文件类型过滤
   - 保留原文件名映射（支持回滚）

**D-Bus服务**: `com.mcp.agent.file`

**工具列表**:
- `file_agent.search_file`
- `file_agent.move_to_trash`
- `file_agent.batch_rename`

---

#### 3.2 SettingsAgent（系统设置智能体）

**位置**: `desktop/agent_project/src/settings_agent_logic.py`, `settings_agent_mcp.py`

**核心功能**:

1. **壁纸设置** (`change_wallpaper`)
   - 修改桌面壁纸
   - 支持5种缩放模式：fill（填充）、stretch（拉伸）、center（居中）、tile（平铺）、zoom（缩放）
   - 基于feh工具实现（虚拟机兼容性优于gsettings）

2. **音量调整** (`adjust_volume`)
   - 调整系统音量（0-100%）
   - 支持指定音频设备
   - 基于pactl实现

3. **蓝牙管理** (`bluetooth_manage`)
   - 开启/关闭蓝牙
   - 连接已配对设备
   - 查询蓝牙状态

**D-Bus服务**: `com.mcp.agent.setting`

**工具列表**:
- `settings_agent.change_wallpaper`
- `settings_agent.adjust_volume`
- `settings_agent.bluetooth_manage`

---

#### 3.3 NetworkAgent（网络管理智能体）

**位置**: `desktop/agent_project/src/network_agent_logic.py`, `network_agent_mcp.py`

**核心功能**:

1. **WiFi管理**
   - `list_wifi`: 扫描可用WiFi网络
   - `connect_wifi`: 连接指定WiFi网络

2. **代理设置** (`set_proxy`)
   - 设置HTTP/HTTPS/SOCKS代理
   - 支持代理清除

3. **网络测速** (`speed_test`)
   - 集成speedtest-cli
   - 支持快速/完整测速模式
   - 返回下载/上传速度

**D-Bus服务**: `com.mcp.agent.network`

**工具列表**:
- `network_agent.list_wifi`
- `network_agent.connect_wifi`
- `network_agent.set_proxy`
- `network_agent.speed_test`

---

#### 3.4 AppAgent（应用管理智能体）

**位置**: `desktop/agent_project/src/app_agent_logic.py`, `app_agent_mcp.py`

**核心功能**:

1. **应用启动** (`launch_app`)
   - 根据应用名称查找并启动应用
   - 支持应用路径启动

2. **应用关闭** (`close_app`)
   - 正常关闭应用
   - 强制关闭应用（kill）

3. **应用快捷操作** (`app_quick_operation`)
   - 支持URL参数启动应用
   - 例如：Firefox打开指定URL

**D-Bus服务**: `com.mcp.agent.app`

**工具列表**:
- `app_agent.launch_app`
- `app_agent.close_app`
- `app_agent.app_quick_operation`

---

#### 3.5 MonitorAgent（系统监控智能体）

**位置**: `desktop/agent_project/src/monitor_agent_logic.py`, `monitor_agent_mcp.py`

**核心功能**:

1. **系统状态查询** (`get_system_status`)
   - CPU使用率
   - 内存使用率
   - 磁盘使用率
   - Top 5进程列表

2. **进程清理** (`clean_background_process`)
   - 清理指定进程
   - 清理所有冗余进程

3. **智能体状态监控**
   - 监控各子智能体的运行状态

**D-Bus服务**: `com.mcp.agent.monitor`

**工具列表**:
- `monitor_agent.get_system_status`
- `monitor_agent.clean_background_process`

---

#### 3.6 MediaAgent（媒体控制智能体）

**位置**: `desktop/agent_project/src/media_agent_logic.py`, `media_agent_mcp.py`

**核心功能**:

1. **媒体播放** (`play_media`)
   - 播放音频/视频文件
   - 支持多种格式

2. **播放控制** (`media_control`)
   - 播放/暂停/停止
   - 全屏切换

3. **截图播放帧** (`capture_media_frame`)
   - 捕获当前播放画面
   - 保存为图片文件

**D-Bus服务**: `com.mcp.agent.media`

**工具列表**:
- `media_agent.play_media`
- `media_agent.media_control`
- `media_agent.capture_media_frame`

---

## 🎨 Web UI 界面

### 技术栈
- **框架**: Gradio
- **访问地址**: `http://localhost:7870`
- **端口**: 7870

### 功能模块

#### 1. 🎯 任务执行
- 统一指令输入框
- 自动推理链解析与展示
- 执行结果展示
- 截图轮播

#### 2. 📁 文件管理
- 文件搜索（关键词、路径、递归选项）
- 批量重命名（规则、前缀、后缀、起始编号）
- 移动到回收站

#### 3. ⚙️ 系统设置
- 壁纸设置（路径、缩放方式、预览）
- 音量调整（滑块、设备选择）
- 蓝牙管理（启用/禁用/状态/连接）

#### 4. 🌐 网络管理
- WiFi扫描与连接
- 代理设置（主机、端口、类型）
- 网络测速（快速/完整模式）

#### 5. 📱 应用管理
- 应用启动（名称输入、快捷启动）
- 应用关闭（运行中应用列表）
- 快捷操作

#### 6. 🧠 记忆轨迹
- 历史任务查询
- 语义检索
- 轨迹可视化
- 推理链复用统计

#### 7. 📜 协作日志
- 全链路日志追溯
- 日志链查询
- 日志统计

#### 8. 📊 系统监控
- 系统状态展示（CPU/内存/磁盘）
- Top 5进程列表
- 进程清理功能
- 自动刷新选项

#### 9. 🎵 媒体控制
- 媒体文件播放
- 播放控制（暂停/继续/停止/全屏）
- 截图播放帧

#### 10. ⚙️ MCP配置
- 智能体权限管理（admin/normal/readonly/guest）
- 配置备份与恢复
- 权限说明文档

---

## 🔄 工作流程

### 完整任务执行流程

```
用户输入任务
    │
    ▼
┌─────────────────────┐
│  指令补全/追问模块   │  ← 如果指令模糊，自动追问
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   记忆检索模块       │  ← 检索相似历史任务
└──────────┬──────────┘
           │
           ├─→ 找到相似任务 → 复用推理链
           │
           └─→ 未找到 → 生成新推理链
                      │
                      ▼
           ┌─────────────────────┐
           │  System-2 推理引擎   │
           │  • 任务分解          │
           │  • 智能体选择        │
           │  • 风险评估          │
           └──────────┬──────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │   推理链格式校验     │
           └──────────┬──────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │   执行计划解析       │
           └──────────┬──────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │   MCP工具调用        │
           │   (按步骤顺序执行)   │
           └──────────┬──────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │   执行结果收集       │
           └──────────┬──────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │   协作轨迹存储       │
           │  (任务+推理链+结果)  │
           └─────────────────────┘
```

### 记忆复用流程

```
新任务输入
    │
    ▼
语义相似度计算
    │
    ├─→ 相似度 ≥ 阈值 → 复用历史推理链
    │                    │
    │                    ▼
    │              直接执行（跳过推理）
    │
    └─→ 相似度 < 阈值 → 生成新推理链
                        │
                        ▼
                   存储到记忆
```

---

## 📁 项目目录结构

```
Kylin-TARS/
├── README.md                          # 项目主README
├── All_In_One.md                      # 本文档（项目全貌）
├── run.sh                             # 主启动脚本
├── config.json                        # 配置文件
│
├── run/                                # 核心运行模块
│   ├── system2_prompt.py              # System-2推理Prompt
│   ├── system2_memory.py              # 推理与记忆整合
│   ├── instruction_completer.py       # 指令补全模块
│   ├── mcp_integration.py             # MCP集成
│   ├── mcp_config.py                  # MCP配置
│   ├── agent_register.py               # 智能体注册
│   └── full_integration.py             # 全链路联调脚本
│
├── memory/                             # 记忆模块
│   ├── memory_store.py                # 轨迹存储
│   ├── memory_retrieve.py             # 高级检索
│   ├── memory_visualization.py        # 可视化
│   └── system2_memory.py              # 推理与记忆整合
│
├── mcp_system/                         # MCP系统
│   ├── mcp_server/                    # MCP服务器
│   │   ├── mcp_server.py              # MCP Server实现
│   │   └── test_mcp_server.py          # 测试脚本
│   └── mcp_client/                     # MCP客户端
│       ├── mcp_client.py               # MCP Client实现
│       └── agent_registry.py           # 智能体注册表
│
├── desktop/agent_project/src/          # 子智能体实现
│   ├── file_agent_logic.py            # FileAgent逻辑
│   ├── file_agent_mcp.py              # FileAgent MCP服务
│   ├── settings_agent_logic.py         # SettingsAgent逻辑
│   ├── settings_agent_mcp.py           # SettingsAgent MCP服务
│   ├── network_agent_logic.py          # NetworkAgent逻辑
│   ├── network_agent_mcp.py            # NetworkAgent MCP服务
│   ├── app_agent_logic.py             # AppAgent逻辑
│   ├── app_agent_mcp.py               # AppAgent MCP服务
│   ├── monitor_agent_logic.py         # MonitorAgent逻辑
│   ├── monitor_agent_mcp.py            # MonitorAgent MCP服务
│   ├── media_agent_logic.py           # MediaAgent逻辑
│   ├── media_agent_mcp.py              # MediaAgent MCP服务
│   └── gradio_upgrade.py               # Gradio UI（升级版）
│
├── utils/                              # 工具模块
│   ├── get_config.py                  # 配置读取
│   └── set_logger.py                   # 日志设置
│
├── log/                                # 日志目录
│   ├── app_agent/                     # AppAgent日志
│   ├── file_agent/                    # FileAgent日志
│   ├── media_agent/                    # MediaAgent日志
│   ├── monitor_agent/                 # MonitorAgent日志
│   ├── network_agent/                  # NetworkAgent日志
│   ├── setting_agent/                 # SettingsAgent日志
│   └── mcp_server/                    # MCP Server日志
│
├── memory/collaboration_memory/        # 协作轨迹存储
│   └── trajectory_*.json              # 历史轨迹文件
│
├── bash/                               # 脚本工具
│   ├── check_dependencies.sh           # 依赖检查
│   ├── check_ports.sh                  # 端口检查
│   ├── start_integration.sh           # 集成启动
│   └── stop_services.sh                # 停止服务
│
├── development_record/                 # 开发记录
│   ├── PROJECT_STATUS.md               # 项目状态
│   ├── COMPLETION_SUMMARY.md           # 完成总结
│   ├── UPGRADE_PROGRESS.md             # 升级进度
│   └── FUNCTION_CHECK_REPORT.md        # 功能检查报告
│
├── requirements.txt                    # Python依赖
├── environment.yml                     # Conda环境配置
└── api_config.sh.example               # API配置模板
```

---

## 🚀 快速开始

### 环境要求

- **操作系统**: openKylin（麒麟操作系统）
- **Python**: 3.10+
- **依赖**: 见 `requirements.txt`

### 安装步骤

#### 1. 克隆项目

```bash
cd /data/usershare/Kylin-TARS
```

#### 2. 创建Conda环境（推荐）

```bash
conda env create -f environment.yml
conda activate uitars-vllm
```

#### 3. 安装Python依赖

```bash
pip install -r requirements.txt
```

#### 4. 安装系统依赖

```bash
sudo apt-get install scrot wmctrl xdotool pulseaudio-utils network-manager
```

#### 5. 配置API（如果使用远程模型）

```bash
mkdir -p ~/.config/kylin-gui-agent
cp api_config.sh.example ~/.config/kylin-gui-agent/api_config.sh
# 编辑配置文件，设置远程服务器地址
nano ~/.config/kylin-gui-agent/api_config.sh
```

### 启动系统

```bash
./run.sh
```

启动后访问: `http://localhost:7870`

### 启动顺序说明

1. **MCP Server** - 首先启动，提供D-Bus服务
2. **6个子智能体** - 依次启动并注册到MCP Server
3. **Gradio UI** - 最后启动，提供Web界面

---

## 🔧 配置说明

### API配置

#### 本地vLLM（默认）

无需配置，系统默认使用 `http://localhost:8000`

#### 远程API

创建 `~/.config/kylin-gui-agent/api_config.sh`:

```bash
export VLLM_API_BASE="http://<服务器IP>:<端口>"
```

### MCP配置

MCP配置位于 `run/mcp_config.py`:

```python
MCP_SERVER_CONFIG = {
    "service_name": "com.kylin.ai.mcp.MasterAgent",
    "object_path": "/com/kylin/ai/mcp/MasterAgent",
    "interface_name": "com.kylin.ai.mcp.MasterAgent",
    "bus_type": "session"
}
```

### 智能体配置

智能体配置位于 `config.json`，包含所有子智能体的D-Bus服务信息。

---

## 📊 核心特性

### 1. System-2 推理

- **任务分解**: 自动将复杂任务拆分为可执行步骤
- **智能体选择**: 根据任务类型选择最合适的智能体
- **风险评估**: 识别执行风险并制定回退策略
- **上下文关联**: 支持步骤间的依赖关系

### 2. 记忆与学习

- **轨迹存储**: 自动存储任务执行轨迹
- **语义检索**: 基于语义相似度检索历史任务
- **推理链复用**: 相似任务自动复用历史推理链
- **用户偏好**: 学习用户操作习惯

### 3. MCP协议

- **统一管理**: 统一的子智能体管理协议
- **负载均衡**: 自动选择最优智能体实例
- **故障转移**: 智能体故障时自动切换
- **状态监控**: 实时监控智能体状态

### 4. 多智能体协作

- **6大专业智能体**: 覆盖文件、设置、网络、应用、监控、媒体等领域
- **统一接口**: 所有智能体通过MCP协议统一调用
- **并行执行**: 支持多任务并行执行

### 5. Web UI

- **统一界面**: 所有功能通过Web界面访问
- **实时反馈**: 实时显示任务执行状态
- **可视化**: 推理链、记忆轨迹可视化展示
- **交互友好**: 支持历史指令快速复用

---

## 🧪 测试与验证

### 依赖检查

```bash
./bash/check_dependencies.sh
```

### 端口检查

```bash
./bash/check_ports.sh
```

### 全链路测试

```bash
cd run
python full_integration.py
```

### 功能测试

```bash
./bash/test_all_upgrades.sh
```

---

## 📝 使用示例

### 示例1: 搜索文件并设置为壁纸

**用户指令**: "把下载目录的png文件设置为壁纸"

**执行流程**:
1. 主Agent理解任务，生成推理链
2. 步骤1: FileAgent搜索 `~/Downloads` 目录下的 `*.png` 文件
3. 步骤2: FileAgent获取第一个png文件路径
4. 步骤3: SettingsAgent设置壁纸
5. 步骤4: SettingsAgent验证壁纸是否生效

**推理链示例**:
```json
{
    "thought_chain": {
        "task_decomposition": "1. 搜索~/Downloads目录下的png文件；2. 选择合适的图片；3. 调用系统设置更换壁纸；4. 验证壁纸是否生效",
        "agent_selection": [
            {"step": 1, "agent": "FileAgent", "reason": "需要文件搜索功能"},
            {"step": 2, "agent": "FileAgent", "reason": "需要文件选择功能"},
            {"step": 3, "agent": "SettingsAgent", "reason": "需要系统设置功能"},
            {"step": 4, "agent": "SettingsAgent", "reason": "需要验证系统状态"}
        ]
    },
    "execution_plan": [
        {"step": 1, "action": "在~/Downloads目录搜索*.png文件", "agent": "FileAgent", "tool": "file_agent.search_file"},
        {"step": 2, "action": "获取搜索结果的第一个png文件路径", "agent": "FileAgent"},
        {"step": 3, "action": "打开系统设置-外观-壁纸，设置选中的图片", "agent": "SettingsAgent", "tool": "settings_agent.change_wallpaper"},
        {"step": 4, "action": "检查桌面壁纸是否已更新", "agent": "SettingsAgent"}
    ]
}
```

### 示例2: 网络测速并调整应用策略

**用户指令**: "测速网络，如果网速慢就关闭视频应用"

**执行流程**:
1. 主Agent理解任务，识别上下文依赖
2. 步骤1: NetworkAgent执行网络测速
3. 步骤2: 根据测速结果（context_ref: step_1），AppAgent关闭视频应用（如果网速慢）

**特点**: 步骤2依赖步骤1的执行结果，体现了上下文关联能力。

---

## 🔍 技术细节

### D-Bus通信

所有智能体间通信基于D-Bus协议：

- **会话总线**: 用于用户级服务
- **系统总线**: 用于系统级服务（如蓝牙）

### 模型适配

系统支持多种模型后端：

- **vLLM**: 本地推理（默认）
- **远程API**: 支持外部API服务
- **模型适配器**: 自动识别模型类型并切换

### 日志系统

- **分级日志**: INFO/WARNING/ERROR
- **日志文件**: 每个智能体独立日志文件
- **协作日志**: 全链路日志追溯

---

## 🐛 故障排查

### 常见问题

#### 1. MCP Server启动失败

**症状**: 子智能体无法注册

**排查**:
```bash
# 检查D-Bus服务
dbus-send --session --print-reply --dest=com.kylin.ai.mcp.MasterAgent /com/kylin/ai/mcp/MasterAgent com.kylin.ai.mcp.MasterAgent.Ping

# 查看日志
tail -f mcp_server.log
```

#### 2. 子智能体注册失败

**症状**: 智能体无法连接到MCP Server

**排查**:
- 确认MCP Server已启动
- 检查D-Bus服务名是否正确
- 查看智能体日志: `log/<agent_name>/`

#### 3. 模型API连接失败

**症状**: 推理链生成失败

**排查**:
```bash
# 测试API连接
curl http://localhost:8000/health

# 检查环境变量
echo $VLLM_API_BASE
```

#### 4. 权限问题

**症状**: 某些操作需要sudo权限

**解决**: 
- 蓝牙操作需要系统D-Bus权限
- 某些系统设置需要管理员权限

---

## 📈 项目状态

### 完成度: 约95%

#### ✅ 已完成功能

- [x] System-2推理引擎
- [x] 记忆存储与检索
- [x] MCP协议实现
- [x] 6大子智能体
- [x] Web UI界面
- [x] 指令补全模块
- [x] 用户偏好学习
- [x] 负载均衡与故障转移

#### ⚠️ 待完善功能

- [ ] 模型适配器实际验证（需要实际环境）
- [ ] API文档编写（可选）
- [ ] 性能优化
- [ ] 更多智能体扩展

---

## 🔮 未来规划

### 短期目标

1. **性能优化**
   - 推理链生成速度优化
   - 记忆检索效率提升

2. **功能扩展**
   - 更多子智能体
   - 更丰富的工具集

3. **用户体验**
   - UI界面优化
   - 错误提示改进

### 长期目标

1. **智能化提升**
   - 更强的任务理解能力
   - 更准确的智能体选择

2. **生态建设**
   - 插件系统
   - 第三方智能体接入

3. **跨平台支持**
   - 支持更多Linux发行版
   - Windows/MacOS支持（可选）

---

## 📚 相关文档

- **README.md**: 项目主文档
- **development_record/PROJECT_STATUS.md**: 项目状态详情
- **development_record/COMPLETION_SUMMARY.md**: 完成总结
- **development_record/README_UPGRADE.md**: 升级版文档
- **API_KEY_CONFIG.md**: API配置指南
- **VM_ENVIRONMENT_SETUP.md**: 虚拟机环境设置

---

## 👥 贡献指南

### 开发规范

1. **代码风格**: 遵循PEP 8
2. **注释**: 所有函数必须有文档字符串
3. **日志**: 使用统一的日志系统
4. **测试**: 新功能必须包含测试

### 提交规范

- 提交信息清晰描述变更内容
- 大功能变更需要更新文档

---

## 📄 许可证

[待补充]

---

## 🙏 致谢

感谢所有为Kylin-TARS项目做出贡献的开发者和用户。

---

**最后更新**: 2024-12

**文档版本**: v1.0

