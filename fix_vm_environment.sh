#!/bin/bash
# 修复虚拟机环境配置脚本
# 解决虚拟环境中无法导入 dbus 和 gi 模块的问题

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  修复虚拟机环境配置                                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 检查是否在虚拟环境中
if [ -z "$VIRTUAL_ENV" ] && [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "⚠️  警告：未检测到虚拟环境"
    echo "请先激活虚拟环境："
    echo "  source venv/bin/activate  # venv"
    echo "  或"
    echo "  conda activate kylin-tars-vm  # conda"
    exit 1
fi

echo "✓ 检测到虚拟环境"
if [ -n "$VIRTUAL_ENV" ]; then
    echo "  虚拟环境路径: $VIRTUAL_ENV"
elif [ -n "$CONDA_DEFAULT_ENV" ]; then
    echo "  Conda 环境: $CONDA_DEFAULT_ENV"
fi
echo ""

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

echo "📋 设置环境变量..."
echo ""

# 设置环境变量
export PYTHONPATH="/usr/lib/python3/dist-packages:$PYTHONPATH"
export GI_TYPELIB_PATH="$GI_LIB_PATH:/usr/share/gir-1.0:${GI_TYPELIB_PATH:-}"
export LD_LIBRARY_PATH="$LD_LIB_PATH:${LD_LIBRARY_PATH:-}"
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=/var/run/dbus/system_bus_socket"

echo "✓ PYTHONPATH: $PYTHONPATH"
echo "✓ GI_TYPELIB_PATH: $GI_TYPELIB_PATH"
echo "✓ LD_LIBRARY_PATH: $LD_LIBRARY_PATH"
echo "✓ DBUS_SYSTEM_BUS_ADDRESS: $DBUS_SYSTEM_BUS_ADDRESS"
echo ""

# 测试模块导入
echo "🔍 测试模块导入..."
python3 << 'PYEOF'
import sys

modules = {
    'dbus': 'dbus',
    'gi': 'gi (PyGObject)',
    'gradio': 'gradio',
    'psutil': 'psutil',
    'requests': 'requests',
    'matplotlib': 'matplotlib',
    'networkx': 'networkx',
    'openai': 'openai',
}

missing = []
for mod, name in modules.items():
    try:
        __import__(mod)
        print(f"✓ {name}")
    except ImportError as e:
        print(f"✗ {name} - 缺失")
        print(f"  错误: {e}")
        missing.append(name)

if missing:
    print(f"\n❌ 缺少模块: {', '.join(missing)}")
    print("\n请检查：")
    print("1. 是否已安装系统包: sudo apt-get install -y python3-gi python3-dbus")
    print("2. 环境变量是否正确设置")
    sys.exit(1)
else:
    print("\n✅ 所有模块检查通过！")
PYEOF

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  ✅ 环境配置成功！                                          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📝 重要提示："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "这些环境变量需要在每次启动服务前设置。"
    echo ""
    echo "方法1：在激活虚拟环境后手动设置（临时）"
    echo "  export PYTHONPATH=\"/usr/lib/python3/dist-packages:\$PYTHONPATH\""
    echo "  export GI_TYPELIB_PATH=\"$GI_LIB_PATH:/usr/share/gir-1.0\""
    echo "  export LD_LIBRARY_PATH=\"$LD_LIB_PATH\""
    echo "  export DBUS_SYSTEM_BUS_ADDRESS=\"unix:path=/var/run/dbus/system_bus_socket\""
    echo ""
    echo "方法2：使用 run_KL.sh 脚本（推荐）"
    echo "  run_KL.sh 会自动设置这些环境变量"
    echo ""
    echo "方法3：在虚拟环境的激活脚本中设置（永久）"
    echo "  编辑: venv/bin/activate"
    echo "  在文件末尾添加上述 export 语句"
    echo ""
else
    echo ""
    echo "❌ 环境配置失败，请检查错误信息"
    exit $EXIT_CODE
fi

