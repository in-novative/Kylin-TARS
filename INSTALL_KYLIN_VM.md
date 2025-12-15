# Kylin-TARS 虚拟机/实机部署指南

## 📋 部署方案概述

本方案适用于在虚拟机或实机上安装openKylin操作系统，uitars推理服务作为外部API调用。

### 架构说明

```
┌─────────────────────────────────────────────────────────┐
│              openKylin系统（虚拟机/实机）                │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Kylin-TARS项目                                  │  │
│  │  ├─ MCP Server                                   │  │
│  │  ├─ 6个子智能体                                 │  │
│  │  ├─ Gradio UI                                    │  │
│  │  └─ 记忆模块                                     │  │
│  └──────────────────────────────────────────────────┘  │
│           │                                             │
│           │ HTTP API                                    │
│           ▼                                             │
└─────────────────────────────────────────────────────────┘
           │
           │ HTTP API (http://uitars-server:8000/v1)
           ▼
┌─────────────────────────────────────────────────────────┐
│          uitars推理服务器（外部）                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │  vLLM API Server                                 │  │
│  │  UI-TARS-1.5-7B模型                              │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 第一部分：系统级依赖安装

### 1. 安装openKylin操作系统

#### 1.1 虚拟机安装（推荐VMware/VirtualBox）

**VMware:**
1. 下载openKylin 2.0 ISO镜像
2. 创建新虚拟机（建议配置：4GB内存，50GB磁盘，启用3D加速）
3. 安装openKylin系统

**VirtualBox:**
1. 下载openKylin 2.0 ISO镜像
2. 创建新虚拟机（建议配置：4GB内存，50GB磁盘，启用3D加速）
3. 安装openKylin系统

#### 1.2 实机安装

1. 制作启动U盘（使用Rufus或balenaEtcher）
2. 从U盘启动，安装openKylin系统
3. 完成系统初始化配置

### 2. 更新系统源

```bash
# 更换为国内镜像源（加速软件包下载）
sudo sed -i 's|http://archive.openkylin.top|https://mirrors.ustc.edu.cn/openkylin|g' /etc/apt/sources.list.d/*.list

# 更新软件包列表
sudo apt update
sudo apt upgrade -y
```

### 3. 安装系统级依赖

#### 3.1 Python环境

```bash
# 检查Python版本（openKylin通常自带Python 3.10+）
python3 --version

# 安装Python开发工具
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential
```

#### 3.2 DBus相关依赖（关键）

```bash
# 安装DBus Python绑定和GTK支持
sudo apt install -y \
    python3-dbus \
    python3-gi \
    gir1.2-gtk-3.0 \
    dbus-x11 \
    libdbus-1-dev \
    libdbus-glib-1-dev \
    libgirepository1.0-dev
```

**安装难度：⭐⭐（简单）**
- ✅ openKylin软件源包含这些包
- ✅ 直接apt安装即可
- ✅ 无需编译

#### 3.3 系统工具

```bash
# 安装常用系统工具
sudo apt install -y \
    curl \
    wget \
    git \
    vim \
    net-tools \
    gnome-terminal \
    nautilus
```

#### 3.4 编译工具（用于编译某些Python包）

```bash
# 安装编译工具（某些Python包需要）
sudo apt install -y \
    gcc \
    g++ \
    make \
    pkg-config \
    libcairo2-dev \
    libgirepository1.0-dev \
    libglib2.0-dev
```

**安装难度：⭐⭐⭐（中等）**
- ✅ 标准Linux工具，openKylin软件源包含
- ⚠️ 需要一定的磁盘空间（约500MB）

---

## 📦 第二部分：Python依赖安装

### 1. 创建Python虚拟环境（推荐）

```bash
# 创建项目目录
mkdir -p ~/kylin-tars
cd ~/kylin-tars

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级pip
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. 安装Python依赖

#### 2.1 使用最小化依赖文件

```bash
# 确保在虚拟环境中
source venv/bin/activate

# 安装依赖（使用清华镜像源加速）
pip install -r requirements-minimal.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 2.2 依赖安装说明

**核心依赖（必需）：**

| 依赖包 | 用途 | 安装难度 | 说明 |
|--------|------|----------|------|
| gradio | Web UI框架 | ⭐ | pip直接安装，简单 |
| psutil | 系统监控 | ⭐ | pip直接安装，简单 |
| dbus-python | DBus通信 | ⭐⭐ | 需要系统级dbus库（已安装） |
| PyGObject | GTK绑定 | ⭐⭐ | 需要系统级gobject库（已安装） |
| requests | HTTP请求 | ⭐ | pip直接安装，简单 |
| json5 | JSON解析 | ⭐ | pip直接安装，简单 |
| Pillow | 图像处理 | ⭐⭐ | 需要系统级图像库（通常已包含） |
| networkx | 网络图 | ⭐ | pip直接安装，简单 |
| matplotlib | 可视化 | ⭐⭐ | 需要系统级字体库（通常已包含） |
| python-dateutil | 日期处理 | ⭐ | pip直接安装，简单 |
| fuzzywuzzy | 模糊匹配 | ⭐ | pip直接安装，简单 |
| python-Levenshtein | 字符串匹配 | ⭐⭐ | 需要编译，但通常无问题 |

**总体安装难度评估：⭐⭐（简单-中等）**

- ✅ 所有依赖都可以通过pip安装
- ✅ 系统级依赖已通过apt安装
- ⚠️ python-Levenshtein可能需要编译（通常自动完成）
- ⚠️ 某些包可能需要系统库支持（已预先安装）

### 3. 验证安装

```bash
# 检查关键依赖
python3 -c "import gradio; print('✓ gradio:', gradio.__version__)"
python3 -c "import dbus; print('✓ dbus-python: OK')"
python3 -c "import gi; print('✓ PyGObject: OK')"
python3 -c "import psutil; print('✓ psutil:', psutil.__version__)"
python3 -c "import networkx; print('✓ networkx:', networkx.__version__)"
python3 -c "import matplotlib; print('✓ matplotlib:', matplotlib.__version__)"
```

---

## 🔧 第三部分：项目配置

### 1. 配置uitars API地址

编辑 `system2_prompt.py` 或设置环境变量：

```bash
# 设置uitars API地址（替换为实际的uitars服务器地址）
export VLLM_API_BASE="http://uitars-server-ip:8000"

# 或在代码中修改
# API_BASE = "http://uitars-server-ip:8000"
```

### 2. 配置项目路径

确保项目文件在正确位置：

```bash
# 假设项目在 ~/kylin-tars
cd ~/kylin-tars

# 检查关键文件
ls -la Desktop/agent_project/src/gradio_upgrade.py
ls -la mcp_system/mcp_server/mcp_server_fixed.py
ls -la start_upgrade.sh
```

### 3. 设置文件权限

```bash
# 确保启动脚本可执行
chmod +x start_upgrade.sh

# 创建必要的目录
mkdir -p screenshots log
```

---

## 🚀 第四部分：启动服务

### 1. 启动Kylin-TARS

```bash
# 激活虚拟环境
source venv/bin/activate

# 设置环境变量（如果需要）
export VLLM_API_BASE="http://uitars-server-ip:8000"

# 启动服务
./start_upgrade.sh
```

### 2. 访问Web UI

在浏览器中访问：
```
http://localhost:7870
```

---

## ⚠️ 常见问题与解决方案

### 1. DBus连接失败

**问题：** `dbus.exceptions.DBusException: org.freedesktop.DBus.Error.NoReply`

**解决方案：**
```bash
# 确保DBus服务运行
sudo systemctl start dbus
sudo systemctl enable dbus

# 检查DBus环境变量
echo $DBUS_SESSION_BUS_ADDRESS

# 如果没有，启动DBus会话
eval $(dbus-launch --sh-syntax)
export DBUS_SESSION_BUS_ADDRESS
```

### 2. PyGObject导入失败

**问题：** `ImportError: No module named 'gi'`

**解决方案：**
```bash
# 重新安装系统包
sudo apt install --reinstall python3-gi gir1.2-gtk-3.0

# 检查GI库路径
python3 -c "import gi; print(gi.__file__)"
```

### 3. python-Levenshtein编译失败

**问题：** 编译python-Levenshtein时出错

**解决方案：**
```bash
# 安装编译依赖
sudo apt install -y python3-dev build-essential

# 重新安装
pip install --no-cache-dir python-Levenshtein
```

### 4. matplotlib字体问题

**问题：** matplotlib中文显示乱码

**解决方案：**
```bash
# 安装中文字体
sudo apt install -y fonts-wqy-microhei fonts-wqy-zenhei

# 清除matplotlib缓存
rm -rf ~/.cache/matplotlib
```

### 5. 网络连接问题（调用uitars API）

**问题：** 无法连接到uitars服务器

**解决方案：**
```bash
# 测试网络连接
curl http://uitars-server-ip:8000/health

# 检查防火墙
sudo ufw status
sudo ufw allow out 8000/tcp

# 检查DNS解析
ping uitars-server-ip
```

---

## 📊 依赖安装难度总结

### 系统级依赖

| 依赖类别 | 安装难度 | 说明 |
|----------|----------|------|
| Python环境 | ⭐ | openKylin自带，简单 |
| DBus相关 | ⭐⭐ | apt直接安装，简单 |
| 编译工具 | ⭐⭐ | 标准工具，简单 |
| 系统工具 | ⭐ | 基础工具，简单 |

### Python依赖

| 依赖类别 | 安装难度 | 说明 |
|----------|----------|------|
| 核心框架（gradio等） | ⭐ | pip直接安装 |
| DBus绑定（dbus-python） | ⭐⭐ | 需要系统库，已安装 |
| 图像处理（Pillow） | ⭐⭐ | 需要系统库，通常已包含 |
| 可视化（matplotlib） | ⭐⭐ | 需要系统库，通常已包含 |
| 字符串匹配（Levenshtein） | ⭐⭐ | 需要编译，通常无问题 |

### 总体评估

**安装难度：⭐⭐（简单-中等）**

✅ **优势：**
- 所有依赖都可以通过标准包管理器安装
- openKylin软件源包含所需系统包
- Python依赖通过pip安装，流程标准
- 无需编译复杂的深度学习框架

⚠️ **注意事项：**
- python-Levenshtein可能需要编译（通常自动完成）
- 某些包需要系统库支持（已预先安装）
- 确保网络连接正常（下载依赖）

---

## 📝 快速安装脚本

创建 `install_kylin_tars.sh`：

```bash
#!/bin/bash
set -e

echo "开始安装Kylin-TARS依赖..."

# 1. 更新系统
sudo apt update

# 2. 安装系统依赖
sudo apt install -y \
    python3 python3-pip python3-venv python3-dev \
    python3-dbus python3-gi gir1.2-gtk-3.0 \
    dbus-x11 libdbus-1-dev libdbus-glib-1-dev libgirepository1.0-dev \
    gcc g++ make pkg-config \
    libcairo2-dev libglib2.0-dev \
    fonts-wqy-microhei fonts-wqy-zenhei

# 3. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 4. 安装Python依赖
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -r requirements-minimal.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "✓ 安装完成！"
echo "激活虚拟环境: source venv/bin/activate"
echo "启动服务: ./start_upgrade.sh"
```

---

## 🎯 下一步

1. 配置uitars API地址
2. 启动Kylin-TARS服务
3. 测试功能
4. 配置开机自启（可选）

