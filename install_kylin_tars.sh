#!/bin/bash
# Kylin-TARS 虚拟机/实机安装脚本
# 适用于：openKylin操作系统

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Kylin-TARS 依赖安装脚本                                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}错误: 请不要使用root用户运行此脚本${NC}"
    exit 1
fi

# 项目目录
PROJECT_DIR=$(dirname "$(readlink -f "$0")")
cd "$PROJECT_DIR"

echo -e "${YELLOW}[1/5] 更新系统软件包列表...${NC}"
sudo apt update

echo ""
echo -e "${YELLOW}[2/5] 安装系统级依赖...${NC}"
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-dbus \
    python3-gi \
    gir1.2-gtk-3.0 \
    dbus-x11 \
    libdbus-1-dev \
    libdbus-glib-1-dev \
    libgirepository1.0-dev \
    gcc \
    g++ \
    make \
    pkg-config \
    libcairo2-dev \
    libglib2.0-dev \
    fonts-wqy-microhei \
    fonts-wqy-zenhei \
    curl \
    wget \
    git \
    vim

echo ""
echo -e "${YELLOW}[3/5] 创建Python虚拟环境...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} 虚拟环境创建成功"
else
    echo -e "${YELLOW}⚠${NC} 虚拟环境已存在，跳过创建"
fi

echo ""
echo -e "${YELLOW}[4/5] 激活虚拟环境并升级pip...${NC}"
source venv/bin/activate
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

echo ""
echo -e "${YELLOW}[5/5] 安装Python依赖...${NC}"
if [ -f "requirements-minimal.txt" ]; then
    pip install -r requirements-minimal.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    echo -e "${GREEN}✓${NC} Python依赖安装完成"
else
    echo -e "${RED}✗${NC} requirements-minimal.txt 不存在"
    exit 1
fi

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  安装完成！                                                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}下一步操作：${NC}"
echo "  1. 激活虚拟环境: ${YELLOW}source venv/bin/activate${NC}"
echo "  2. 配置uitars API地址（编辑 system2_prompt.py 或设置环境变量）"
echo "  3. 启动服务: ${YELLOW}./start_upgrade.sh${NC}"
echo ""
echo -e "${YELLOW}注意：${NC}"
echo "  - uitars推理服务需要单独部署（外部API）"
echo "  - 确保uitars服务器可访问"
echo "  - 设置环境变量: export VLLM_API_BASE=\"http://uitars-server-ip:8000\""

