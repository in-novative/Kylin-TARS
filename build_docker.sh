#!/bin/bash
# 构建 Kylin-TARS Docker 镜像脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

IMAGE_NAME="kylin-tars"
IMAGE_TAG="latest"
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  构建 Kylin-TARS Docker 镜像                                 ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检查 Dockerfile 是否存在
if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}✗ 错误: Dockerfile 不存在${NC}"
    exit 1
fi

# 检查 requirements.txt 是否存在
if [ ! -f "requirements.txt" ]; then
    echo -e "${YELLOW}⚠️  警告: requirements.txt 不存在，将创建默认版本${NC}"
    # 这里可以自动生成 requirements.txt
fi

echo -e "${BLUE}[步骤 1/3] 检查 Docker 环境${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker 已安装${NC}"
echo ""

echo -e "${BLUE}[步骤 2/3] 构建 Docker 镜像${NC}"
echo "  镜像名称: ${FULL_IMAGE_NAME}"
echo "  这可能需要几分钟时间..."
echo ""

docker build \
    --tag ${FULL_IMAGE_NAME} \
    --progress=plain \
    --no-cache \
    .

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ 镜像构建成功！${NC}"
else
    echo ""
    echo -e "${RED}✗ 镜像构建失败${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}[步骤 3/3] 验证镜像${NC}"
docker images | grep ${IMAGE_NAME} | head -1

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ 构建完成！                                                ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "下一步操作:"
echo ""
echo "1. 启动容器（使用 docker-compose）:"
echo "   ${CYAN}docker-compose up -d${NC}"
echo ""
echo "2. 或手动启动容器:"
echo "   ${CYAN}docker run -it --privileged --network host \\${NC}"
echo "   ${CYAN}  -v /data1:/data1 -v /data2:/data2 \\${NC}"
echo "   ${CYAN}  -e DISPLAY=:99 -e VLLM_API_BASE=http://<服务器IP>:<端口> \\${NC}"
echo "   ${CYAN}  ${FULL_IMAGE_NAME}${NC}"
echo ""
echo "3. 进入容器:"
echo "   ${CYAN}docker exec -it kylin-tars bash${NC}"
echo ""
echo "4. 启动服务:"
echo "   ${CYAN}cd /data1/cyx/Kylin-TARS${NC}"
echo "   ${CYAN}bash docker_run.sh${NC}"
echo ""

