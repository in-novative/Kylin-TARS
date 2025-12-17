# Kylin 虚拟机环境配置指南

## 概述

本文档提供在 Kylin 虚拟机上配置 Kylin-TARS GUI Agent 环境的完整指南。

**重要说明**：
- UITARS 推理服务部署在远程服务器上，虚拟机不需要 CUDA 支持
- 虚拟机只需要运行 GUI Agent 客户端，通过 API 调用远程 UITARS 服务
- 需要图形界面环境（GNOME 桌面）以支持媒体控制、截图等功能

---

## 一、系统要求

### 1.1 操作系统
- **openKylin** 或 **Ubuntu Kylin**（基于 Ubuntu 22.04+）
- 已安装 GNOME 桌面环境
- 已配置图形界面（X11 或 Wayland）

### 1.2 系统包依赖

```bash
# 更新系统包
sudo apt-get update

# 安装系统依赖
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    gir1.2-glib-2.0 \
    dbus \
    dbus-x11 \
    libdbus-1-dev \
    libgirepository1.0-dev \
    pkg-config \
    build-essential \
    git \
    curl \
    wget

# 安装截图工具（用于媒体控制和壁纸截图）
sudo apt-get install -y \
    gnome-screenshot \
    scrot

# 安装媒体播放器（用于媒体控制）
sudo apt-get install -y \
    totem

# 安装键盘工具（用于媒体控制备用方案）
sudo apt-get install -y \
    xdotool
```

---

## 二、Python 环境配置

### 2.1 方法一：使用 Conda（推荐）

#### 2.1.1 安装 Miniconda（如果未安装）

```bash
# 下载 Miniconda
cd /tmp
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# 安装
bash Miniconda3-latest-Linux-x86_64.sh

# 重新加载 shell
source ~/.bashrc
```

#### 2.1.2 创建 Conda 环境

```bash
# 进入项目目录
cd /path/to/Kylin-TARS

# 使用虚拟机专用环境文件创建环境
conda env create -f environment_vm.yml

# 激活环境
conda activate kylin-tars-vm
```

#### 2.1.3 验证环境

```bash
# 检查 Python 版本
python --version  # 应该是 Python 3.10.x

# 检查关键模块
python -c "import gradio; import dbus; import gi; import psutil; print('所有模块导入成功')"
```

---

### 2.2 方法二：使用 Python venv

#### 2.2.1 创建虚拟环境

```bash
# 进入项目目录
cd /path/to/Kylin-TARS

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

#### 2.2.2 安装 Python 依赖

```bash
# 升级 pip
pip install --upgrade pip

# 安装系统包依赖（重要：必须在安装 pip 包之前）
# PyGObject 和 dbus-python 需要通过系统包安装
sudo apt-get install -y python3-gi python3-dbus

# 安装 Python 包
pip install -r requirements_vm.txt

# ⚠️ 重要：设置环境变量，让虚拟环境能够访问系统包
# 检测系统架构
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    GI_LIB_PATH="/usr/lib/x86_64-linux-gnu/girepository-1.0"
    LD_LIB_PATH="/usr/lib/x86_64-linux-gnu"
elif [ "$ARCH" = "aarch64" ]; then
    GI_LIB_PATH="/usr/lib/aarch64-linux-gnu/girepository-1.0"
    LD_LIB_PATH="/usr/lib/aarch64-linux-gnu"
else
    GI_LIB_PATH="/usr/lib/girepository-1.0"
    LD_LIB_PATH="/usr/lib"
fi

# 设置环境变量（当前会话）
export PYTHONPATH="/usr/lib/python3/dist-packages:$PYTHONPATH"
export GI_TYPELIB_PATH="$GI_LIB_PATH:/usr/share/gir-1.0"
export LD_LIBRARY_PATH="$LD_LIB_PATH"
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=/var/run/dbus/system_bus_socket"

# 验证模块导入
python3 -c "import dbus; import gi; print('✓ dbus 和 gi 模块可用')"
```

**注意**：这些环境变量需要在每次激活虚拟环境后设置，或者使用 `run_KL.sh` 脚本（会自动设置）。

#### 2.2.3 验证环境

```bash
# 检查关键模块
python -c "import gradio; import dbus; import gi; import psutil; print('所有模块导入成功')"
```

---

## 三、环境变量配置

### 3.1 创建配置文件

```bash
# 创建配置目录
mkdir -p ~/.config/kylin-gui-agent

# 创建 API 配置文件
cat > ~/.config/kylin-gui-agent/api_config.sh << 'EOF'
#!/bin/bash
# UITARS API 配置
# 将 YOUR_SERVER_IP 替换为实际的服务器 IP 地址

export UITARS_API_BASE="http://YOUR_SERVER_IP:8000"
# 或者如果使用其他端口
# export UITARS_API_BASE="http://YOUR_SERVER_IP:PORT"

# 可选：设置 API Key（如果服务器启用了认证）
# export UITARS_API_KEY="your-api-key-here"
EOF

# 赋予执行权限
chmod +x ~/.config/kylin-gui-agent/api_config.sh
```

### 3.2 编辑配置文件

使用文本编辑器编辑 `~/.config/kylin-gui-agent/api_config.sh`，将 `YOUR_SERVER_IP` 替换为实际的 UITARS 服务器 IP 地址。

**示例**：
```bash
export UITARS_API_BASE="http://192.168.1.100:8000"
```

---

## 四、验证环境配置

### 4.1 检查图形界面环境

```bash
# 检查 DISPLAY 环境变量
echo $DISPLAY
# 应该输出类似 :0 或 :1

# 或者检查 Wayland
echo $WAYLAND_DISPLAY
# Wayland 环境下应该有输出
```

### 4.2 检查 DBus

```bash
# 检查 DBus Session Bus
dbus-run-session -- echo "DBus available"
# 应该输出 "DBus available"

# 检查 DBus System Bus（用于蓝牙等功能）
echo $DBUS_SYSTEM_BUS_ADDRESS
# 应该输出 unix:path=/var/run/dbus/system_bus_socket
```

### 4.3 检查 Python 模块

```bash
# 激活环境（如果使用 conda）
conda activate kylin-tars-vm

# 或者激活 venv
source venv/bin/activate

# 运行检查脚本
python3 << 'EOF'
import sys

modules = [
    'gradio',
    'dbus',
    'gi',
    'psutil',
    'requests',
    'matplotlib',
    'networkx',
    'openai',
]

missing = []
for mod in modules:
    try:
        __import__(mod)
        print(f"✓ {mod}")
    except ImportError:
        print(f"✗ {mod} - 缺失")
        missing.append(mod)

if missing:
    print(f"\n缺少模块: {', '.join(missing)}")
    sys.exit(1)
else:
    print("\n所有模块检查通过！")
EOF
```

### 4.4 检查系统工具

```bash
# 检查截图工具
which gnome-screenshot scrot
# 应该输出两个路径

# 检查媒体播放器
which totem
# 应该输出 /usr/bin/totem

# 检查键盘工具
which xdotool
# 应该输出 /usr/bin/xdotool
```

---

## 五、常见问题排查

### 5.1 PyGObject 和 DBus 导入错误（虚拟环境）

**错误信息**：
```
ImportError: No module named 'gi'
ImportError: No module named 'dbus'
```

**原因**：`dbus` 和 `gi` (PyGObject) 是通过系统包安装的，位于 `/usr/lib/python3/dist-packages/`，但虚拟环境默认无法访问系统包路径。

**解决方法**：

**方法1：使用修复脚本（推荐）**
```bash
# 激活虚拟环境
source venv/bin/activate

# 运行修复脚本
bash fix_vm_environment.sh
```

**方法2：手动设置环境变量**
```bash
# 激活虚拟环境
source venv/bin/activate

# 检测系统架构并设置环境变量
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    GI_LIB_PATH="/usr/lib/x86_64-linux-gnu/girepository-1.0"
    LD_LIB_PATH="/usr/lib/x86_64-linux-gnu"
elif [ "$ARCH" = "aarch64" ]; then
    GI_LIB_PATH="/usr/lib/aarch64-linux-gnu/girepository-1.0"
    LD_LIB_PATH="/usr/lib/aarch64-linux-gnu"
else
    GI_LIB_PATH="/usr/lib/girepository-1.0"
    LD_LIB_PATH="/usr/lib"
fi

export PYTHONPATH="/usr/lib/python3/dist-packages:$PYTHONPATH"
export GI_TYPELIB_PATH="$GI_LIB_PATH:/usr/share/gir-1.0"
export LD_LIBRARY_PATH="$LD_LIB_PATH"
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=/var/run/dbus/system_bus_socket"

# 验证
python3 -c "import dbus; import gi; print('✓ 模块可用')"
```

**方法3：在虚拟环境激活脚本中永久设置**
```bash
# 编辑虚拟环境激活脚本
nano venv/bin/activate

# 在文件末尾添加（根据系统架构调整路径）：
export PYTHONPATH="/usr/lib/python3/dist-packages:$PYTHONPATH"
export GI_TYPELIB_PATH="/usr/lib/x86_64-linux-gnu/girepository-1.0:/usr/share/gir-1.0"
export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu"
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=/var/run/dbus/system_bus_socket"
```

**方法4：使用 run_KL.sh（最简单）**
```bash
# run_KL.sh 会自动设置这些环境变量
./run_KL.sh
```

### 5.2 DBus 连接错误

**错误信息**：
```
dbus.exceptions.DBusException: org.freedesktop.DBus.Error.NoReply
```

**解决方法**：
```bash
# 确保 DBus 服务正在运行
sudo systemctl status dbus

# 确保在图形界面会话中运行
# 不要在 SSH 会话中直接运行，需要使用 X11 转发或图形界面
```

### 5.3 图形界面功能不可用

**症状**：媒体控制、截图等功能报错

**解决方法**：
```bash
# 检查图形界面环境
echo $DISPLAY
echo $WAYLAND_DISPLAY

# 如果为空，需要设置 DISPLAY
export DISPLAY=:0

# 或者使用 xhost 允许访问
xhost +local:
```

### 5.4 UITARS API 连接失败

**错误信息**：
```
ConnectionError: Failed to connect to UITARS API
```

**解决方法**：
```bash
# 1. 检查网络连接
ping YOUR_SERVER_IP

# 2. 检查 API 地址配置
cat ~/.config/kylin-gui-agent/api_config.sh

# 3. 测试 API 连接
curl http://YOUR_SERVER_IP:8000/health

# 4. 检查防火墙
# 确保服务器端口 8000 已开放
```

---

## 六、启动服务

### 6.1 使用 run_KL.sh（推荐）

```bash
# 确保在项目根目录
cd /path/to/Kylin-TARS

# 确保已激活环境
conda activate kylin-tars-vm
# 或
source venv/bin/activate

# 运行启动脚本
./run_KL.sh
```

### 6.2 手动启动（调试用）

```bash
# 激活环境
conda activate kylin-tars-vm

# 设置环境变量
export PYTHONPATH="/usr/lib/python3/dist-packages:$PYTHONPATH"
export GI_TYPELIB_PATH="/usr/lib/x86_64-linux-gnu/girepository-1.0:/usr/share/gir-1.0:$GI_TYPELIB_PATH"
export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"

# 启动服务
dbus-run-session -- python3 desktop/agent_project/src/gradio_upgrade.py
```

---

## 七、环境配置检查清单

在启动服务前，请确认以下项目：

- [ ] 系统包已安装（python3-gi, dbus, gnome-screenshot 等）
- [ ] Python 环境已创建并激活
- [ ] Python 依赖包已安装
- [ ] UITARS API 地址已配置（`~/.config/kylin-gui-agent/api_config.sh`）
- [ ] 图形界面环境可用（DISPLAY 或 WAYLAND_DISPLAY）
- [ ] DBus Session Bus 可用
- [ ] 所有 Python 模块导入成功
- [ ] 系统工具可用（totem, gnome-screenshot, xdotool）

---

## 八、与服务器环境的区别

| 项目 | 服务器环境 | 虚拟机环境 |
|------|-----------|-----------|
| CUDA 支持 | ✅ 需要 | ❌ 不需要 |
| vLLM | ✅ 需要 | ❌ 不需要 |
| PyTorch | ✅ 需要（GPU） | ❌ 不需要 |
| UITARS API | ✅ 本地运行 | ❌ 远程调用 |
| 图形界面 | ❌ 不需要 | ✅ 需要 |
| DBus | ✅ 需要 | ✅ 需要 |
| PyGObject | ✅ 需要 | ✅ 需要 |
| Gradio | ✅ 需要 | ✅ 需要 |

---

## 九、更新和维护

### 9.1 更新 Python 依赖

```bash
# 激活环境
conda activate kylin-tars-vm

# 更新 pip 包
pip install --upgrade -r requirements_vm.txt
```

### 9.2 更新系统包

```bash
sudo apt-get update
sudo apt-get upgrade
```

---

## 十、联系支持

如果遇到问题，请提供：
1. 操作系统版本：`lsb_release -a`
2. Python 版本：`python --version`
3. 环境检查输出：运行第四节的验证脚本
4. 错误日志：`logs/startup_*.log`

