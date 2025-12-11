# Kylin-TARS GUI Agent 升级版

## 📋 项目概述

Kylin-TARS 升级版是一个基于 openKylin 桌面的多智能体 GUI 操作系统，集成了 6 个专业智能体，提供统一的 Web 界面进行任务管理和系统操作。

## 🚀 核心特性

### 1. 多智能体架构

- **FileAgent** - 文件管理智能体
  - 文件搜索（递归/非递归）
  - 移动到回收站
  - 文件信息查询

- **SettingsAgent** - 系统设置智能体
  - 桌面壁纸设置（5种缩放模式）
  - 系统音量调整
  - 音频设备管理
  - 蓝牙管理（开启/关闭/连接/状态查询）

- **NetworkAgent** - 网络管理智能体
  - WiFi 网络扫描
  - WiFi 连接管理
  - 系统代理设置（HTTP/HTTPS/SOCKS）
  - 网络测速（快速/完整模式）

- **AppAgent** - 应用管理智能体
  - 应用查找和启动
  - 应用关闭（正常/强制）
  - 运行中应用列表
  - 应用快捷操作（支持URL参数）

- **MonitorAgent** - 系统监控智能体
  - 系统状态查询（CPU/内存/磁盘）
  - 后台进程清理
  - 智能体状态监控

- **MediaAgent** - 媒体控制智能体
  - 音频/视频播放
  - 媒体播放控制（播放/暂停/停止）
  - 截图播放帧

### 2. 升级版 Web UI

- **6模块布局**
  - 🎯 任务执行：统一指令输入，自动推理链解析
  - 📁 文件管理：文件搜索和操作
  - ⚙️ 系统设置：壁纸、音量和蓝牙管理
  - 🌐 网络管理：WiFi、代理设置和网络测速
  - 📱 应用管理：应用启动、关闭和快捷操作
  - 🧠 记忆轨迹：历史任务查询、语义检索、轨迹可视化
  - 📜 协作日志：全链路日志追溯、日志链查询

- **交互增强**
  - 历史指令下拉框（快速复用）
  - 推理链 JSON 格式化展示（关键字段高亮）
  - 实时日志流
  - 截图轮播展示
  - 一键复制推理链

- **演示模式**
  - 预设演示任务（搜索+壁纸、网络+浏览器、音量调整）
  - 一键快速测试

- **权限控制**
  - 演示模式开关（`DEMO_MODE=true/false`）
  - 操作确认机制（`REQUIRE_CONFIRMATION=true/false`）

## 📦 项目结构

```
Kylin-TARS/
├── Desktop/agent_project/src/
│   ├── agent_template.py          # 子智能体开发模板
│   ├── file_agent_logic.py         # FileAgent 核心逻辑
│   ├── file_agent_mcp.py          # FileAgent MCP 服务
│   ├── settings_agent_logic.py     # SettingsAgent 核心逻辑
│   ├── settings_agent_mcp.py       # SettingsAgent MCP 服务
│   ├── network_agent_logic.py     # NetworkAgent 核心逻辑
│   ├── network_agent_mcp.py        # NetworkAgent MCP 服务
│   ├── app_agent_logic.py          # AppAgent 核心逻辑
│   ├── app_agent_mcp.py           # AppAgent MCP 服务
│   ├── monitor_agent_logic.py      # MonitorAgent 核心逻辑
│   ├── monitor_agent_mcp.py        # MonitorAgent MCP 服务
│   ├── media_agent_logic.py        # MediaAgent 核心逻辑
│   ├── media_agent_mcp.py          # MediaAgent MCP 服务
│   └── gradio_upgrade.py           # 升级版 Gradio UI
├── mcp_system/mcp_server/
│   └── mcp_server_fixed.py         # MCP Server（主控）
├── start_upgrade.sh                # 升级版启动脚本
├── test_upgrade.sh                 # 功能测试脚本
├── test_all_upgrades.sh            # 全面升级测试脚本
├── memory_store.py                 # 记忆存储模块（用户偏好学习）
├── memory_retrieve.py              # 记忆检索模块（语义检索）
├── memory_visualization.py         # 记忆可视化模块
├── collaboration_logger.py         # 协作日志模块
├── model_adapter.py                # 模型适配层（Qwen2.5系列）
├── mcp_config_manager.py           # MCP配置管理模块
└── README_UPGRADE.md              # 本文档
```

## 🛠️ 安装与配置

### 环境要求

- openKylin 操作系统
- Python 3.10+
- Conda 环境：`uitars-vllm`
- 系统工具：`scrot`, `wmctrl`, `xdotool`, `pactl`, `nmcli`

### 依赖安装

```bash
# 激活环境
conda activate uitars-vllm

# 安装 Python 依赖
pip install gradio psutil dbus-python PyGObject requests json5

# 安装系统工具（如果缺失）
sudo apt-get install scrot wmctrl xdotool pulseaudio-utils network-manager
```

### 配置远程 API（如果模型部署在远程服务器）

如果您的 uitars 模型部署在远程服务器上，需要配置 API 连接：

#### 方式 1：使用配置文件（推荐）

```bash
# 创建配置目录
mkdir -p ~/.config/kylin-gui-agent

# 复制配置模板
cp api_config.sh.example ~/.config/kylin-gui-agent/api_config.sh

# 编辑配置文件，修改服务器地址
nano ~/.config/kylin-gui-agent/api_config.sh
# 设置: export VLLM_API_BASE="http://<服务器IP>:<端口>"
```

#### 方式 2：使用环境变量

```bash
# 临时设置（当前会话有效）
export VLLM_API_BASE="http://192.168.1.100:8000"

# 永久设置（添加到 ~/.bashrc）
echo 'export VLLM_API_BASE="http://192.168.1.100:8000"' >> ~/.bashrc
source ~/.bashrc
```

#### 测试远程 API 连接

```bash
# 设置 API 地址（如果使用环境变量）
export VLLM_API_BASE="http://<服务器IP>:<端口>"

# 运行测试脚本
python3 test_remote_api.py
```

**详细迁移指南请参考**: `MIGRATION_GUIDE.md`

## 🎮 使用方法

### 1. 启动系统

```bash
cd /data1/cyx/Kylin-TARS
./start_upgrade.sh
```

启动脚本会自动：
1. 启动 MCP Server（主控服务，支持负载均衡和故障转移）
2. 启动 6 个子智能体（FileAgent, SettingsAgent, NetworkAgent, AppAgent, MonitorAgent, MediaAgent）
3. 启动 Gradio Web UI（默认端口 7870）

### 2. 访问 Web UI

浏览器打开：`http://localhost:7870`

### 3. 功能测试

运行测试脚本验证所有功能：

```bash
# 基础功能测试
./test_upgrade.sh

# 全面升级测试（检查所有模块）
./test_all_upgrades.sh
```

## 📖 使用示例

### 示例 1：文件搜索 + 壁纸设置

1. 在「任务执行」页面输入：
   ```
   搜索下载目录的png文件并设置为壁纸
   ```

2. 点击「▶️ 执行任务」

3. 系统会自动：
   - 调用 FileAgent 搜索 `~/Downloads` 目录下的 PNG 文件
   - 调用 SettingsAgent 设置第一个找到的 PNG 为壁纸
   - 显示推理链和执行结果

### 示例 2：网络状态 + 启动浏览器

1. 输入：
   ```
   获取当前网络状态，然后启动Firefox浏览器
   ```

2. 系统会：
   - 调用 NetworkAgent 获取 WiFi 和代理状态
   - 调用 AppAgent 启动 Firefox

### 示例 3：音量调整

1. 输入：
   ```
   把系统音量调到50%
   ```

2. 系统会：
   - 调用 SettingsAgent 调整音量到 50%

### 示例 4：使用演示模式

点击「📁 搜索+壁纸」按钮，自动填充预设任务并执行。

## 🔧 配置选项

### 环境变量

在启动脚本或系统环境中设置：

```bash
# 演示模式开关（默认：true）
export DEMO_MODE=true

# 操作确认机制（默认：false）
export REQUIRE_CONFIRMATION=false

# Gradio 端口（默认：7870）
export GRADIO_SERVER_PORT=7870
```

### 权限控制

如果启用 `REQUIRE_CONFIRMATION=true`，用户在执行任务前需要勾选「✓ 我已确认执行此操作」复选框。

## 🧪 开发指南

### 添加新智能体

1. **复制模板**：
   ```bash
   cp Desktop/agent_project/src/agent_template.py Desktop/agent_project/src/new_agent_logic.py
   ```

2. **实现核心逻辑**：
   - 继承 `BaseAgentLogic`
   - 实现 `make_response()` 方法
   - 添加工具函数（如 `do_something()`）

3. **创建 MCP 服务**：
   ```bash
   cp Desktop/agent_project/src/agent_template_mcp.py Desktop/agent_project/src/new_agent_mcp.py
   ```
   - 定义工具元数据 `NEW_AGENT_TOOLS`
   - 实现 `handle_tool_call()` 函数
   - 注册到 MCP Server

4. **集成到 Gradio UI**：
   - 在 `gradio_upgrade.py` 中添加新标签页
   - 绑定事件处理函数

5. **更新启动脚本**：
   - 在 `start_upgrade.sh` 中添加启动命令

## 📊 系统架构

```
┌─────────────────────────────────────────┐
│         Gradio Web UI (前端)             │
│    gradio_upgrade.py                    │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         MCP Server (主控)               │
│    mcp_server_fixed.py                  │
└──────┬──────┬──────┬──────┬────────────┘
       │      │      │      │
       ▼      ▼      ▼      ▼
    File   Settings Network  App
   Agent   Agent    Agent   Agent
```

## 🐛 故障排查

### 问题 1：端口被占用

**解决方案**：
- Gradio UI 会自动查找可用端口（7870-7879）
- 或手动设置：`export GRADIO_SERVER_PORT=8888`

### 问题 2：子智能体未启动

**检查**：
```bash
# 检查 MCP Server 是否运行
dbus-send --session --print-reply \
  --dest=com.kylin.ai.mcp.MasterAgent \
  /com/kylin/ai/mcp/MasterAgent \
  com.kylin.ai.mcp.MasterAgent.ToolsList

# 检查子智能体是否注册
ps aux | grep agent_mcp.py
```

### 问题 3：截图功能不可用

**解决方案**：
```bash
# 安装截图工具
sudo apt-get install scrot

# 或使用 gnome-screenshot
sudo apt-get install gnome-screenshot
```

### 问题 4：网络功能不可用

**检查**：
```bash
# 检查 NetworkManager 服务
systemctl status NetworkManager

# 检查 nmcli 命令
which nmcli
```

## 📝 更新日志

### v3.0 (全面升级版)

**模块一：System-2推理与智能体扩展**
- ✅ 扩展System-2推理Prompt（多轮上下文、新功能识别）
- ✅ 新增指令补全/追问模块
- ✅ 新增MonitorAgent（系统监控）
- ✅ 新增MediaAgent（媒体控制）
- ✅ 功能扩展：批量重命名、蓝牙管理、网络测速、应用快捷操作

**模块二：记忆与检索**
- ✅ 用户偏好学习模块（常用路径、高频工具、重命名规则）
- ✅ 语义检索功能（支持麒麟AI框架，无则回退关键词检索）
- ✅ 记忆轨迹可视化（networkx关联图）

**模块三：MCP系统优化**
- ✅ MCP负载均衡和故障转移（CPU占用最低优先）
- ✅ 智能体状态广播机制（每3秒心跳，状态变更广播）
- ✅ 协作全链路日志追溯（决策/调度/执行/广播日志）

**模块四：模型适配**
- ✅ 模型适配层（支持Qwen2.5-0.5B/1.5B/3B/7B/14B系列）
- ✅ 模型自动切换逻辑（健康检查+自动切换）

**模块五：MCP配置管理**
- ✅ MCP配置面板（Gradio集成）
- ✅ MCP角色权限分级（admin/normal/readonly/guest）
- ✅ MCP配置自动备份/恢复（定时备份）

### v2.0 (升级版)

- ✅ 新增 NetworkAgent（WiFi 和代理管理）
- ✅ 新增 AppAgent（应用启动和关闭）
- ✅ 升级 Gradio UI（6模块布局 + 交互增强）
- ✅ 实现演示模式和权限控制
- ✅ 添加子智能体开发模板
- ✅ 完善错误处理和日志系统

### v1.0 (基础版)

- ✅ FileAgent（文件搜索、移动到回收站）
- ✅ SettingsAgent（壁纸设置、音量调整）
- ✅ 基础 Gradio UI
- ✅ MCP 协议集成

## 📄 许可证

本项目为内部项目，仅供学习和研究使用。

## 👥 贡献者

- GUI Agent Team

## 📧 联系方式

如有问题或建议，请联系项目维护团队。

---

**最后更新**：2024-12

