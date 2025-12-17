# Kylin 虚拟机快速开始指南

## 一、环境准备（一次性配置）

### 1. 安装系统依赖

```bash
sudo apt-get update
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
    gnome-screenshot \
    scrot \
    totem \
    xdotool
```

### 2. 创建 Python 环境

**方法一：使用 Conda（推荐）**

```bash
# 创建环境
conda env create -f environment_vm.yml

# 激活环境
conda activate kylin-tars-vm
```

**方法二：使用 venv**

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements_vm.txt
```

### 3. 配置 UITARS API 地址

```bash
# 创建配置目录
mkdir -p ~/.config/kylin-gui-agent

# 创建配置文件（替换 YOUR_SERVER_IP 为实际服务器IP）
cat > ~/.config/kylin-gui-agent/api_config.sh << 'CONFIG'
#!/bin/bash
export UITARS_API_BASE="http://YOUR_SERVER_IP:8000"
CONFIG

# 赋予执行权限
chmod +x ~/.config/kylin-gui-agent/api_config.sh
```

**重要**：将 `YOUR_SERVER_IP` 替换为实际的 UITARS 服务器 IP 地址。

---

## 二、启动服务

### 1. 确保环境已激活

```bash
# Conda 环境
conda activate kylin-tars-vm

# 或 venv 环境
source venv/bin/activate
```

### 2. 运行启动脚本

```bash
cd /path/to/Kylin-TARS
./run_KL.sh
```

### 3. 访问 Web UI

启动成功后，在浏览器中访问：
```
http://localhost:7870
```

---

## 三、验证环境

运行以下命令验证环境配置：

```bash
# 检查 Python 版本
python --version  # 应该是 Python 3.10.x

# 检查关键模块
python -c "import gradio; import dbus; import gi; import psutil; print('✓ 所有模块可用')"

# 检查图形界面
echo "DISPLAY: $DISPLAY"
echo "WAYLAND_DISPLAY: $WAYLAND_DISPLAY"

# 检查 DBus
dbus-run-session -- echo "✓ DBus 可用"

# 检查系统工具
which gnome-screenshot totem xdotool
```

---

## 四、常见问题

### 问题1：PyGObject 导入错误

**错误**：`ImportError: No module named 'gi'`

**解决**：
```bash
sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0
```

### 问题2：UITARS API 连接失败

**错误**：`ConnectionError: Failed to connect to UITARS API`

**解决**：
1. 检查 API 地址配置：`cat ~/.config/kylin-gui-agent/api_config.sh`
2. 测试网络连接：`ping YOUR_SERVER_IP`
3. 测试 API：`curl http://YOUR_SERVER_IP:8000/health`

### 问题3：图形界面功能不可用

**错误**：媒体控制、截图等功能报错

**解决**：
```bash
# 检查图形界面环境
echo $DISPLAY
# 如果为空，设置 DISPLAY
export DISPLAY=:0
```

---

## 五、与服务器环境的区别

| 项目 | 服务器环境 | 虚拟机环境 |
|------|-----------|-----------|
| CUDA | ✅ 需要 | ❌ 不需要 |
| vLLM | ✅ 本地运行 | ❌ 不需要 |
| PyTorch | ✅ 需要（GPU） | ❌ 不需要 |
| UITARS | ✅ 本地运行 | ✅ 远程调用 |
| 图形界面 | ❌ 不需要 | ✅ 需要 |
| DBus | ✅ 需要 | ✅ 需要 |

---

## 六、更新项目

```bash
# 拉取最新代码
git pull

# 更新 Python 依赖（如果 requirements_vm.txt 有更新）
pip install --upgrade -r requirements_vm.txt
```

---

## 七、获取帮助

如果遇到问题：
1. 查看详细文档：`VM_ENVIRONMENT_SETUP.md`
2. 查看启动日志：`logs/startup_*.log`
3. 运行环境检查脚本（见第三部分）

