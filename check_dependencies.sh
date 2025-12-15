#!/bin/bash
# Kylin-TARS 依赖检查脚本
#
# 检查项目运行所需的所有依赖：
# - Python包
# - 系统工具
# - DBus服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  🔍 Kylin-TARS 依赖检查                                      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

MISSING=0
OPTIONAL_MISSING=0

# 检查函数
check_python_package() {
    local package=$1
    local required=${2:-true}
    
    echo -n "检查 Python 包: $package... "
    if python -c "import $package" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 已安装${NC}"
        return 0
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}✗ 缺失（必需）${NC}"
            ((MISSING++))
            return 1
        else
            echo -e "${YELLOW}⊘ 缺失（可选）${NC}"
            ((OPTIONAL_MISSING++))
            return 1
        fi
    fi
}

check_system_tool() {
    local tool=$1
    local required=${2:-true}
    
    echo -n "检查系统工具: $tool... "
    if command -v $tool > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 已安装${NC}"
        return 0
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}✗ 缺失（必需）${NC}"
            ((MISSING++))
            return 1
        else
            echo -e "${YELLOW}⊘ 缺失（可选）${NC}"
            ((OPTIONAL_MISSING++))
            return 1
        fi
    fi
}

# ============================================================
# Python包检查
# ============================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Python 包检查${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

check_python_package "gradio" true
check_python_package "psutil" true
check_python_package "dbus" true
check_python_package "gi" true  # PyGObject
check_python_package "json5" false
check_python_package "networkx" false
check_python_package "matplotlib" false
check_python_package "sentence_transformers" false
check_python_package "fuzzywuzzy" false

echo ""

# ============================================================
# 系统工具检查
# ============================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}系统工具检查${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

check_system_tool "scrot" false
check_system_tool "gnome-screenshot" false
check_system_tool "wmctrl" false
check_system_tool "xdotool" false
check_system_tool "pactl" true
check_system_tool "nmcli" true
check_system_tool "gsettings" true
check_system_tool "dbus-send" true
check_system_tool "gio" false
check_system_tool "totem" false

echo ""

# ============================================================
# DBus服务检查
# ============================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}DBus 服务检查${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -n "检查 DBus 会话总线... "
if dbus-send --session --print-reply --dest=org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.ListNames > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 可用${NC}"
else
    echo -e "${RED}✗ 不可用${NC}"
    ((MISSING++))
fi

echo ""

# ============================================================
# 检查总结
# ============================================================
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  检查总结                                                      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ $MISSING -eq 0 ]; then
    echo -e "${GREEN}✓ 所有必需依赖已安装${NC}"
    if [ $OPTIONAL_MISSING -gt 0 ]; then
        echo -e "${YELLOW}⚠ 有 $OPTIONAL_MISSING 个可选依赖缺失（不影响核心功能）${NC}"
    fi
    echo ""
    echo "安装可选依赖的命令："
    echo "  pip install json5 networkx matplotlib sentence-transformers fuzzywuzzy python-Levenshtein"
    echo "  sudo apt-get install scrot gnome-screenshot wmctrl xdotool"
    exit 0
else
    echo -e "${RED}✗ 有 $MISSING 个必需依赖缺失${NC}"
    if [ $OPTIONAL_MISSING -gt 0 ]; then
        echo -e "${YELLOW}⚠ 还有 $OPTIONAL_MISSING 个可选依赖缺失${NC}"
    fi
    echo ""
    echo "安装命令："
    echo "  pip install gradio psutil dbus-python PyGObject"
    echo "  sudo apt-get install pulseaudio-utils network-manager"
    exit 1
fi

