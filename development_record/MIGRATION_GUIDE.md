# Kylin-TARS 项目迁移到真实Kylin操作系统指南

## 📋 迁移概述

本指南将帮助您将 Kylin-TARS 项目从开发环境迁移到真实的 Kylin 操作系统，并配置远程 uitars 模型服务器连接。

## 🎯 迁移前准备

### 1. 环境检查清单

在真实 Kylin 系统上检查以下内容：

```bash
# 检查操作系统版本
cat /etc/os-release

# 检查 Python 版本（需要 3.10+）
python3 --version

# 检查 Conda 环境
conda --version

# 检查系统工具
which scrot wmctrl xdotool pactl nmcli dbus-send
```

### 2. 网络连接检查

确保 Kylin 系统能够访问部署 uitars 模型的服务器：

```bash
# 测试网络连通性（替换为您的服务器IP）
ping <服务器IP>

# 测试 API 端口（替换为您的服务器IP和端口）
curl http://<服务器IP>:<端口>/health
curl http://<服务器IP>:<端口>/v1/models
```

## 📦 迁移步骤

### 步骤 1：传输项目文件

将项目文件传输到 Kylin 系统：

```bash
# 方式1：使用 scp（在开发机器上执行）
scp -r /data1/cyx/Kylin-TARS user@kylin-host:/path/to/destination/

# 方式2：使用 rsync（推荐，支持断点续传）
rsync -avz --progress /data1/cyx/Kylin-TARS/ user@kylin-host:/path/to/destination/Kylin-TARS/

# 方式3：使用 Git（如果项目已提交）
git clone <repository-url> /path/to/destination/Kylin-TARS
```

### 步骤 2：安装系统依赖

在 Kylin 系统上安装必要的系统工具：

```bash
sudo apt-get update
sudo apt-get install -y \
    scrot \
    wmctrl \
    xdotool \
    pulseaudio-utils \
    network-manager \
    dbus \
    python3-dbus \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0
```

### 步骤 3：配置 Python 环境

```bash
# 激活或创建 Conda 环境
conda activate uitars-vllm  # 如果已存在
# 或创建新环境
conda create -n uitars-vllm python=3.10 -y
conda activate uitars-vllm

# 安装 Python 依赖
cd /path/to/Kylin-TARS
pip install -r requirements_system2.txt
pip install gradio psutil dbus-python PyGObject requests json5
```

### 步骤 4：配置远程 API 连接

#### 方式 1：使用环境变量（推荐）

创建配置文件 `~/.config/kylin-gui-agent/api_config.sh`：

```bash
#!/bin/bash
# Kylin-TARS API 配置

# 远程 uitars 模型服务器地址
export VLLM_API_BASE="http://<服务器IP>:<端口>"
# 示例：export VLLM_API_BASE="http://192.168.1.100:8000"

# 模型名称（可选，如果服务器有多个模型）
export VLLM_MODEL_NAME="UI-TARS-1.5-7B"

# API 超时设置（秒）
export VLLM_API_TIMEOUT=120

# 是否启用 SSL（如果使用 HTTPS）
export VLLM_API_SSL=false
```

然后在启动脚本中加载配置：

```bash
# 在 start_upgrade.sh 开头添加
if [ -f ~/.config/kylin-gui-agent/api_config.sh ]; then
    source ~/.config/kylin-gui-agent/api_config.sh
fi
```

#### 方式 2：修改代码配置

如果不想使用环境变量，可以直接修改代码：

1. **修改 `model_adapter.py`**：
   ```python
   # 第35行，修改默认 API 地址
   def __init__(self, api_base: str = None):
       if api_base is None:
           api_base = os.getenv("VLLM_API_BASE", "http://<服务器IP>:<端口>")
   ```

2. **修改 `system2_prompt.py`**：
   ```python
   # 第37行，修改 API_BASE
   API_BASE = os.getenv("VLLM_API_BASE", "http://<服务器IP>:<端口>")
   ```

### 步骤 5：配置模型路径（可选）

如果模型路径不同，修改 `model_adapter.py` 中的模型配置：

```python
# 修改 ~/.config/kylin-gui-agent/model_config.json
{
    "UI-TARS-1.5-7B": {
        "path": "/path/to/model/on/server",  # 服务器上的模型路径
        "type": "UI-TARS-7B",
        "priority": 1,
        "max_tokens": 2048,
        "temperature": 0.7
    }
}
```

**注意**：如果使用远程 API，模型路径通常不需要配置，因为模型在服务器上。

### 步骤 6：测试连接

创建测试脚本 `test_remote_api.py`：

```python
#!/usr/bin/env python3
import os
import requests
import sys

# 从环境变量读取配置
api_base = os.getenv("VLLM_API_BASE", "http://localhost:8000")

print(f"测试 API 连接: {api_base}")

# 测试健康检查
try:
    response = requests.get(f"{api_base}/health", timeout=5)
    if response.status_code == 200:
        print("✓ 健康检查通过")
    else:
        print(f"✗ 健康检查失败: {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"✗ 健康检查失败: {e}")
    sys.exit(1)

# 测试模型列表
try:
    response = requests.get(f"{api_base}/v1/models", timeout=5)
    if response.status_code == 200:
        models = response.json()
        print(f"✓ 可用模型: {models}")
    else:
        print(f"✗ 获取模型列表失败: {response.status_code}")
except Exception as e:
    print(f"✗ 获取模型列表失败: {e}")

# 测试简单生成
try:
    response = requests.post(
        f"{api_base}/v1/completions",
        json={
            "model": "test",
            "prompt": "Hello",
            "max_tokens": 10
        },
        timeout=10
    )
    if response.status_code == 200:
        print("✓ API 调用成功")
    else:
        print(f"⚠️ API 调用返回: {response.status_code}")
except Exception as e:
    print(f"⚠️ API 调用测试失败: {e}")

print("\n✓ 所有测试完成")
```

运行测试：

```bash
source ~/.config/kylin-gui-agent/api_config.sh  # 如果使用环境变量
python3 test_remote_api.py
```

### 步骤 7：启动服务

```bash
cd /path/to/Kylin-TARS
./start_upgrade.sh
```

## 🔧 常见问题排查

### 问题 1：无法连接到远程 API

**症状**：`Connection refused` 或 `Timeout`

**解决方案**：
1. 检查服务器防火墙是否开放端口
2. 检查网络连通性：`ping <服务器IP>`
3. 检查 API 地址是否正确：`curl http://<服务器IP>:<端口>/health`
4. 如果使用 HTTPS，检查证书配置

### 问题 2：API 返回 401/403 错误

**症状**：`Unauthorized` 或 `Forbidden`

**解决方案**：
1. 检查服务器是否需要 API Key
2. 如果使用 API Key，在 `model_adapter.py` 中添加：
   ```python
   headers = {
       "Authorization": f"Bearer {os.getenv('VLLM_API_KEY', '')}"
   }
   ```

### 问题 3：模型路径错误

**症状**：`Model not found` 或模型加载失败

**解决方案**：
1. 如果使用远程 API，不需要配置本地模型路径
2. 检查服务器上的模型是否正确加载
3. 使用 `/v1/models` 端点查看可用模型列表

### 问题 4：DBus 连接失败

**症状**：`DBus connection failed`

**解决方案**：
```bash
# 检查 DBus 服务
systemctl status dbus

# 检查用户会话 DBus
dbus-send --session --print-reply --dest=org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.ListNames
```

### 问题 5：权限不足

**症状**：无法执行某些系统操作

**解决方案**：
```bash
# 检查用户权限
groups

# 可能需要添加到特定组
sudo usermod -aG audio,video,input $USER
```

## 📝 配置示例

### 完整配置示例

创建 `~/.config/kylin-gui-agent/config.json`：

```json
{
    "api": {
        "base_url": "http://192.168.1.100:8000",
        "timeout": 120,
        "ssl": false,
        "api_key": ""
    },
    "model": {
        "default": "UI-TARS-1.5-7B",
        "max_tokens": 2048,
        "temperature": 0.7
    },
    "system": {
        "gradio_port": 7870,
        "log_level": "INFO"
    }
}
```

### 启动脚本示例

修改 `start_upgrade.sh` 添加配置加载：

```bash
#!/bin/bash
# ... 其他代码 ...

# 加载 API 配置
CONFIG_DIR="$HOME/.config/kylin-gui-agent"
if [ -f "$CONFIG_DIR/api_config.sh" ]; then
    source "$CONFIG_DIR/api_config.sh"
fi

# 设置默认值
export VLLM_API_BASE="${VLLM_API_BASE:-http://localhost:8000}"

echo "API 配置: $VLLM_API_BASE"

# ... 启动服务 ...
```

## 🔐 安全建议

1. **使用 HTTPS**：如果可能，使用 HTTPS 连接保护 API 通信
2. **API Key**：如果服务器支持，使用 API Key 进行身份验证
3. **防火墙**：限制 API 端口的访问范围
4. **VPN**：如果服务器在公网，建议使用 VPN 连接

## 📊 性能优化

1. **连接池**：如果频繁调用 API，考虑使用连接池
2. **超时设置**：根据网络情况调整超时时间
3. **重试机制**：已实现自动重试，可根据需要调整重试次数
4. **缓存**：对于相同请求，可以考虑添加缓存

## ✅ 迁移检查清单

- [ ] 项目文件已传输到 Kylin 系统
- [ ] 系统依赖已安装
- [ ] Python 环境已配置
- [ ] 远程 API 地址已配置
- [ ] API 连接测试通过
- [ ] 所有智能体服务正常启动
- [ ] Gradio UI 可以正常访问
- [ ] 基本功能测试通过

## 📞 获取帮助

如果遇到问题：

1. 查看日志文件：`mcp_server.log`
2. 运行诊断脚本：`./check_dependencies.sh`
3. 检查端口占用：`./check_ports.sh`
4. 查看项目文档：`README_UPGRADE.md`

---

**最后更新**：2024-12

