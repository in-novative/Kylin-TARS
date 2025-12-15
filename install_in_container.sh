#!/bin/bash
# 在 openKylin Docker 容器内安装和配置 Kylin-TARS 项目

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_DIR="/home/kylin-user/kylin-tars-project"

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  在容器内安装 Kylin-TARS 项目                               ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检查项目目录是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}⚠ 项目目录不存在: $PROJECT_DIR${NC}"
    echo "  请确保项目已正确挂载到容器内"
    exit 1
fi

cd "$PROJECT_DIR"

echo -e "${BLUE}[1/4] 检查 Python 环境...${NC}"
python3 --version
pip3 --version
echo -e "${GREEN}✓ Python 环境检查完成${NC}"
echo ""

echo -e "${BLUE}[2/4] 安装 Python 依赖...${NC}"
if [ -f "requirements.txt" ]; then
    pip3 install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
    pip3 install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
        -r requirements.txt
    echo -e "${GREEN}✓ requirements.txt 安装完成${NC}"
else
    echo -e "${YELLOW}⚠ requirements.txt 不存在，跳过${NC}"
fi

if [ -f "requirements_system2.txt" ]; then
    pip3 install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
        -r requirements_system2.txt || true
    echo -e "${GREEN}✓ requirements_system2.txt 安装完成${NC}"
else
    echo -e "${YELLOW}⚠ requirements_system2.txt 不存在，跳过${NC}"
fi
echo ""

echo -e "${BLUE}[3/4] 检查系统依赖...${NC}"
MISSING_TOOLS=0

check_tool() {
    if command -v $1 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $1 已安装${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ $1 未安装${NC}"
        ((MISSING_TOOLS++))
        return 1
    fi
}

check_tool "scrot"
check_tool "wmctrl"
check_tool "xdotool"
check_tool "pactl"
check_tool "nmcli"
check_tool "gsettings"
check_tool "dbus-send"

if [ $MISSING_TOOLS -gt 0 ]; then
    echo -e "${YELLOW}⚠ 有 $MISSING_TOOLS 个工具缺失，尝试安装...${NC}"
    sudo apt update && sudo apt install -y \
        scrot wmctrl xdotool pulseaudio-utils network-manager || true
fi
echo ""

echo -e "${BLUE}[4/4] 配置项目...${NC}"
# 创建必要的目录
mkdir -p screenshots log data/memory data/config
echo -e "${GREEN}✓ 目录创建完成${NC}"

# 设置脚本执行权限
if [ -f "start_upgrade.sh" ]; then
    chmod +x start_upgrade.sh
    echo -e "${GREEN}✓ 启动脚本权限设置完成${NC}"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ 项目安装完成！                                            ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "下一步操作:"
echo "  1. 启动项目:"
echo "     ${CYAN}cd $PROJECT_DIR && ./start_upgrade.sh${NC}"
echo ""
echo "  2. 或手动启动各个服务:"
echo "     ${CYAN}cd $PROJECT_DIR${NC}"
echo "     ${CYAN}python3 mcp_system/mcp_server/mcp_server_fixed.py &${NC}"
echo "     ${CYAN}python3 Desktop/agent_project/src/gradio_upgrade.py${NC}"
echo ""

