#!/bin/bash
# 构建 Kylin-TARS openKylin Docker 镜像脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

IMAGE_NAME="kylin-tars-openkylin"
IMAGE_TAG="${IMAGE_TAG:-latest}"
DOCKERFILE="${DOCKERFILE:-Dockerfile.openkylin}"

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  构建 Kylin-TARS openKylin Docker 镜像                       ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检查 Dockerfile 是否存在
if [ ! -f "$DOCKERFILE" ]; then
    echo -e "${RED}✗ Dockerfile 不存在: $DOCKERFILE${NC}"
    exit 1
fi

# 检查 requirements 文件是否存在
if [ ! -f "requirements.txt" ]; then
    echo -e "${YELLOW}⚠ requirements.txt 不存在，将使用默认依赖${NC}"
fi

# 获取用户 ID 和组 ID（用于匹配宿主机权限）
USER_ID=${USER_ID:-$(id -u)}
GROUP_ID=${GROUP_ID:-$(id -g)}
USER_NAME=${USER_NAME:-kylin-user}
USER_PASS=${USER_PASS:-kylin123}

echo -e "${BLUE}[构建配置]${NC}"
echo "  镜像名称: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "  Dockerfile: $DOCKERFILE"
echo "  用户 ID: $USER_ID"
echo "  组 ID: $GROUP_ID"
echo "  用户名: $USER_NAME"
echo ""

# 配置 Docker 国内镜像源（如果未配置）
if [ ! -f /etc/docker/daemon.json ]; then
    echo -e "${YELLOW}⚠ 检测到 Docker 未配置国内镜像源，建议配置以加速构建${NC}"
    echo "  执行以下命令配置（需要 sudo 权限）："
    echo "  sudo mkdir -p /etc/docker"
    echo "  sudo tee /etc/docker/daemon.json <<-'EOF'"
    echo "  {"
    echo "    \"registry-mirrors\": ["
    echo "      \"https://docker.mirrors.ustc.edu.cn\","
    echo "      \"https://hub-mirror.c.163.com\""
    echo "    ]"
    echo "  }"
    echo "  EOF"
    echo "  sudo systemctl daemon-reload && sudo systemctl restart docker"
    echo ""
fi

# 开始构建
echo -e "${BLUE}[开始构建]${NC}"
echo "  这可能需要几分钟时间，请耐心等待..."
echo ""

docker build \
    --build-arg USER_ID=$USER_ID \
    --build-arg GROUP_ID=$GROUP_ID \
    --build-arg USER_NAME=$USER_NAME \
    --build-arg USER_PASS=$USER_PASS \
    -f "$DOCKERFILE" \
    -t "${IMAGE_NAME}:${IMAGE_TAG}" \
    .

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ 镜像构建成功！                                            ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "镜像信息:"
    docker images | grep "$IMAGE_NAME" | head -1
    echo ""
    echo "下一步操作:"
    echo "  1. 启动容器:"
    echo "     ${CYAN}./start_docker_openkylin.sh${NC}"
    echo ""
    echo "  2. 或使用 docker-compose:"
    echo "     ${CYAN}docker-compose -f docker-compose.openkylin.yml up -d${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}✗ 镜像构建失败${NC}"
    exit 1
fi

