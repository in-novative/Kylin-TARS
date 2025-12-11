# Kylin-TARS 升级版开发进度

## ✅ 已完成模块

### 模块一：指令理解+规划决策+接口调用优化

#### ✅ 1.1 扩展System-2推理Prompt
- [x] 支持多轮上下文关联（context_ref字段）
- [x] 新增工具识别（tool_extend字段）
- [x] 更新推理链格式验证函数
- [x] 添加MonitorAgent和MediaAgent到可用智能体列表

#### ✅ 1.2 指令补全/追问模块
- [x] 创建 `instruction_completer.py`
- [x] 实现模糊指令判断（参数缺失/指令歧义/依赖缺失）
- [x] 自动生成追问话术
- [x] 支持用户补充参数后重新生成推理链

#### ✅ 1.3 新增MonitorAgent和MediaAgent
- [x] MonitorAgent核心逻辑 (`monitor_agent_logic.py`)
  - [x] 获取系统状态（CPU/内存/磁盘）
  - [x] 清理后台进程
  - [x] 监控智能体状态
- [x] MonitorAgent MCP服务 (`monitor_agent_mcp.py`)
- [x] MediaAgent核心逻辑 (`media_agent_logic.py`)
  - [x] 播放媒体文件
  - [x] 媒体控制（播放/暂停/停止/全屏）
  - [x] 截图播放帧
- [x] MediaAgent MCP服务 (`media_agent_mcp.py`)

#### ✅ 1.4 现有智能体扩展功能（部分完成）
- [x] FileAgent: 批量重命名功能 (`file_agent_logic.py`)
  - [x] 支持4种重命名规则（prefix_seq/date_prefix_seq/suffix_seq/date_suffix_seq）
  - [x] 文件类型过滤
  - [x] 保留原文件名映射用于回滚
- [x] FileAgent MCP注册 (`file_agent_mcp.py`)

## 🚧 进行中/待完成模块

### 模块一：现有智能体扩展功能（剩余部分）

#### ⏳ SettingsAgent扩展
- [ ] 蓝牙管理功能 (`settings_agent_logic.py`)
  - [ ] 开启/关闭蓝牙
  - [ ] 连接已配对设备
  - [ ] 查询蓝牙状态
- [ ] SettingsAgent MCP注册更新

#### ⏳ NetworkAgent扩展
- [ ] 网络测速功能 (`network_agent_logic.py`)
  - [ ] 集成speedtest-cli
  - [ ] 支持快速/完整测速切换
- [ ] NetworkAgent MCP注册更新

#### ⏳ AppAgent扩展
- [ ] 应用快捷操作 (`app_agent_logic.py`)
  - [ ] 定义主流应用参数映射
  - [ ] 支持URL参数（如firefox https://www.baidu.com）
- [ ] AppAgent MCP注册更新

### 模块二：记忆+检索历史操作优化

#### ⏳ 用户偏好学习模块
- [ ] 扩展 `memory_store.py`
  - [ ] 偏好数据采集（常用路径/高频工具/操作习惯）
  - [ ] 偏好存储结构 (`user_preference.json`)
  - [ ] 偏好应用（推理链生成时注入）

#### ⏳ 语义检索功能
- [ ] 接入麒麟AI框架语义检索（可选）
- [ ] 保留关键词检索作为备选

#### ⏳ 记忆轨迹可视化
- [ ] Gradio集成可视化组件
- [ ] 使用networkx绘制轨迹关联图
- [ ] 支持筛选和节点点击查看

### 模块三：智能体交互协作优化

#### ⏳ MCP负载均衡和故障转移
- [ ] 在`mcp_server.py`中新增`load_balance`函数
- [ ] 实现故障转移机制`fault_tolerance`
- [ ] 多实例智能体CPU占用查询

#### ⏳ 智能体状态广播机制
- [ ] 状态定义（online/busy/offline/error）
- [ ] 心跳机制（每3秒）
- [ ] DBus信号广播

#### ⏳ 协作全链路日志追溯
- [ ] 日志结构定义 (`collaboration_log.json`)
- [ ] 日志记录时机（决策/调度/执行/广播）
- [ ] Gradio日志展示模块

### 模块四：兼容大模型+麒麟AI框架优化

#### ⏳ 模型适配层
- [ ] 创建`model_adapter.py`
- [ ] 支持Qwen2.5系列模型
- [ ] 统一推理接口

#### ⏳ 模型自动切换逻辑
- [ ] 显存不足检测
- [ ] 推理超时检测
- [ ] 模型加载失败处理

#### ⏳ 加速能力
- [ ] QNNPACK加速配置
- [ ] TensorRT加速（GPU环境）
- [ ] CPU量化加速（无GPU环境）

### 模块五：MCP Server配置能力优化

#### ⏳ MCP配置面板（Gradio集成）
- [ ] 基础配置面板
- [ ] 超时配置面板
- [ ] 状态监控面板
- [ ] 配置持久化 (`mcp_config.json`)

#### ⏳ MCP角色权限分级
- [ ] 角色定义（普通用户/管理员）
- [ ] 权限校验逻辑
- [ ] 管理员认证

#### ⏳ MCP配置自动备份/恢复
- [ ] 自动备份机制
- [ ] 一键恢复功能
- [ ] 备份目录管理

## 📝 技术说明

### 已实现的关键技术点

1. **多轮上下文关联**：通过`context_ref`字段实现步骤间依赖关系
2. **工具扩展标记**：通过`tool_extend`字段区分新增工具
3. **指令补全机制**：自动检测参数缺失并生成追问
4. **批量重命名回滚**：保留原文件名映射，支持回滚操作

### 文件结构

```
Kylin-TARS/
├── system2_prompt.py              # ✅ 已扩展
├── instruction_completer.py       # ✅ 新增
├── Desktop/agent_project/src/
│   ├── monitor_agent_logic.py     # ✅ 新增
│   ├── monitor_agent_mcp.py       # ✅ 新增
│   ├── media_agent_logic.py       # ✅ 新增
│   ├── media_agent_mcp.py         # ✅ 新增
│   ├── file_agent_logic.py         # ✅ 已扩展（批量重命名）
│   └── file_agent_mcp.py          # ✅ 已更新
└── UPGRADE_PROGRESS.md            # 本文档
```

## 🎯 下一步计划

1. **完成现有智能体扩展功能**（SettingsAgent蓝牙、NetworkAgent测速、AppAgent快捷操作）
2. **实现用户偏好学习模块**
3. **开发MCP负载均衡和故障转移**
4. **集成模型适配层**（优先Qwen2.5系列）
5. **开发MCP配置面板**

## 📌 注意事项

- 所有新增功能需遵循现有MCP协议规范
- 保持代码风格一致性
- 每个模块完成后需进行单元测试
- 优先实现核心功能，可视化等增强功能可后续迭代

