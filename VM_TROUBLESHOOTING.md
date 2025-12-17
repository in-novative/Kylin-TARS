# 虚拟机环境问题排查指南

## 问题1：虚拟环境中无法导入 dbus 和 gi 模块

### 症状
```bash
python3 -c "import dbus; import gi"
# ImportError: No module named 'dbus'
# ImportError: No module named 'gi'
```

### 原因
- `dbus` 和 `gi` (PyGObject) 是通过系统包安装的（`python3-dbus`, `python3-gi`）
- 这些模块位于 `/usr/lib/python3/dist-packages/`
- 虚拟环境默认无法访问系统包路径

### 解决方案

#### 方案1：使用修复脚本（最简单）

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 运行修复脚本
bash fix_vm_environment.sh

# 3. 验证
python3 -c "import dbus; import gi; print('✓ 成功')"
```

#### 方案2：手动设置环境变量

```bash
# 激活虚拟环境
source venv/bin/activate

# 设置环境变量（根据系统架构调整）
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
python3 -c "import dbus; import gi; print('✓ 成功')"
```

#### 方案3：在虚拟环境激活脚本中永久设置

```bash
# 编辑激活脚本
nano venv/bin/activate

# 在文件末尾添加（根据你的系统架构调整）：
export PYTHONPATH="/usr/lib/python3/dist-packages:$PYTHONPATH"
export GI_TYPELIB_PATH="/usr/lib/x86_64-linux-gnu/girepository-1.0:/usr/share/gir-1.0"
export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu"
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=/var/run/dbus/system_bus_socket"

# 重新激活虚拟环境
deactivate
source venv/bin/activate
```

#### 方案4：使用 run_KL.sh（推荐）

`run_KL.sh` 脚本会自动设置这些环境变量，无需手动配置：

```bash
# 直接运行即可
./run_KL.sh
```

---

## 问题2：DBus 警告信息

### 症状
```bash
dbus-run-session -- echo "test"
# dbus[xxxxx]: Unknown username "kylin" in message bus configuration file
# test
```

### 原因
- DBus 配置文件中引用了不存在的用户 "kylin"
- 这是配置警告，**不影响功能**

### 解决方案
可以忽略此警告，不影响使用。如果想消除警告：

```bash
# 检查 DBus 配置文件
grep -r "kylin" /etc/dbus-1/

# 如果找到相关配置，可以注释掉或删除
# 但通常不需要修改，警告不影响功能
```

---

## 问题3：DBUS_SYSTEM_BUS_ADDRESS 未设置

### 症状
```bash
echo $DBUS_SYSTEM_BUS_ADDRESS
# （空输出）
```

### 解决方案
```bash
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=/var/run/dbus/system_bus_socket"
```

或者在 `run_KL.sh` 中会自动设置。

---

## 问题4：图形界面环境检查

### 检查 DISPLAY 和 WAYLAND_DISPLAY

```bash
echo $DISPLAY
echo $WAYLAND_DISPLAY
```

如果两者都为空，需要设置：

```bash
# X11 环境
export DISPLAY=:0

# Wayland 环境（通常自动设置）
# export WAYLAND_DISPLAY=wayland-0
```

---

## 完整的环境检查脚本

运行以下脚本检查所有环境配置：

```bash
#!/bin/bash
echo "=== 环境检查 ==="
echo ""

echo "1. 虚拟环境："
if [ -n "$VIRTUAL_ENV" ]; then
    echo "   ✓ 虚拟环境: $VIRTUAL_ENV"
elif [ -n "$CONDA_DEFAULT_ENV" ]; then
    echo "   ✓ Conda 环境: $CONDA_DEFAULT_ENV"
else
    echo "   ✗ 未激活虚拟环境"
fi

echo ""
echo "2. 图形界面："
if [ -n "$DISPLAY" ]; then
    echo "   ✓ DISPLAY: $DISPLAY"
elif [ -n "$WAYLAND_DISPLAY" ]; then
    echo "   ✓ WAYLAND_DISPLAY: $WAYLAND_DISPLAY"
else
    echo "   ✗ 未设置图形界面环境变量"
fi

echo ""
echo "3. 环境变量："
echo "   PYTHONPATH: ${PYTHONPATH:-未设置}"
echo "   GI_TYPELIB_PATH: ${GI_TYPELIB_PATH:-未设置}"
echo "   LD_LIBRARY_PATH: ${LD_LIBRARY_PATH:-未设置}"
echo "   DBUS_SYSTEM_BUS_ADDRESS: ${DBUS_SYSTEM_BUS_ADDRESS:-未设置}"

echo ""
echo "4. Python 模块："
python3 << 'PYEOF'
import sys
modules = ['dbus', 'gi', 'gradio', 'psutil', 'requests', 'matplotlib', 'networkx', 'openai']
missing = []
for mod in modules:
    try:
        __import__(mod)
        print(f"   ✓ {mod}")
    except ImportError:
        print(f"   ✗ {mod}")
        missing.append(mod)
if missing:
    print(f"\n   缺少模块: {', '.join(missing)}")
    sys.exit(1)
PYEOF

echo ""
echo "5. 系统工具："
for tool in gnome-screenshot totem xdotool; do
    if command -v $tool &> /dev/null; then
        echo "   ✓ $tool: $(which $tool)"
    else
        echo "   ✗ $tool: 未找到"
    fi
done

echo ""
echo "=== 检查完成 ==="
```

---

## 快速修复命令

如果遇到 `dbus` 和 `gi` 导入错误，运行：

```bash
# 激活虚拟环境
source venv/bin/activate

# 设置环境变量
ARCH=$(uname -m)
[ "$ARCH" = "x86_64" ] && GI_LIB="/usr/lib/x86_64-linux-gnu/girepository-1.0" || GI_LIB="/usr/lib/girepository-1.0"
[ "$ARCH" = "x86_64" ] && LD_LIB="/usr/lib/x86_64-linux-gnu" || LD_LIB="/usr/lib"

export PYTHONPATH="/usr/lib/python3/dist-packages:$PYTHONPATH"
export GI_TYPELIB_PATH="$GI_LIB:/usr/share/gir-1.0"
export LD_LIBRARY_PATH="$LD_LIB_PATH"
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=/var/run/dbus/system_bus_socket"

# 验证
python3 -c "import dbus, gi; print('✓ 成功')"
```

---

## 联系支持

如果问题仍然存在，请提供：
1. 操作系统版本：`lsb_release -a`
2. Python 版本：`python --version`
3. 虚拟环境类型：venv 或 conda
4. 完整的错误信息
5. 环境检查脚本的输出

