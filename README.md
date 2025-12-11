# Kylin-TARS GUI Agent

## 📋 项目简介

Kylin-TARS 是一个基于 openKylin 桌面的多智能体 GUI 操作系统，集成了 6 个专业智能体，提供统一的 Web 界面进行任务管理和系统操作。

## 🚀 快速开始

### 1. 环境准备

```bash
# 激活 Conda 环境
conda activate uitars-vllm

# 安装依赖
pip install gradio psutil dbus-python PyGObject requests json5
sudo apt-get install scrot wmctrl xdotool pulseaudio-utils network-manager
```

### 2. 配置远程 API（如果模型在远程服务器）

```bash
# 复制配置模板
mkdir -p ~/.config/kylin-gui-agent
cp api_config.sh.example ~/.config/kylin-gui-agent/api_config.sh

# 编辑配置文件，设置远程服务器地址
nano ~/.config/kylin-gui-agent/api_config.sh
# 修改: export VLLM_API_BASE="http://<服务器IP>:<端口>"

# 测试连接
python3 test_remote_api.py
```

### 3. 启动服务

```bash
./start_upgrade.sh
```

访问 Web UI: `http://localhost:7870`

## 📚 文档

- **升级版详细文档**: [README_UPGRADE.md](README_UPGRADE.md)
- **迁移指南**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
- **项目状态**: [PROJECT_STATUS.md](PROJECT_STATUS.md)

## 🎯 核心功能

- **6 个专业智能体**: FileAgent, SettingsAgent, NetworkAgent, AppAgent, MonitorAgent, MediaAgent
- **System-2 推理**: 任务分解、智能体选择、风险评估
- **记忆与检索**: 用户偏好学习、语义检索、轨迹可视化
- **MCP 负载均衡**: 自动故障转移和状态监控
- **Web UI**: 统一的 Gradio 界面

## 🔧 配置说明

### 本地开发（模型在同一台机器）

默认配置即可，无需修改。

### 远程服务器（模型在另一台机器）

1. 创建配置文件 `~/.config/kylin-gui-agent/api_config.sh`
2. 设置 `VLLM_API_BASE` 环境变量
3. 运行 `test_remote_api.py` 验证连接

详细说明请参考 [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)

## 📞 获取帮助

- 查看日志: `mcp_server.log`
- 运行诊断: `./check_dependencies.sh`
- 检查端口: `./check_ports.sh`

---

**最后更新**: 2024-12

