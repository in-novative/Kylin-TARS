#!/bin/bash
# Kylin-TARS GUI Agent 全链路联调启动脚本
#
# 使用方式：
#   1. 模拟模式（无需D-Bus）: ./start_integration.sh --mock
#   2. 完整模式（需要D-Bus）: ./start_integration.sh
#
# 启动顺序：
#   1. MCP Server (成员A)
#   2. 子智能体注册适配器
#   3. Gradio界面 (成员C)
#   4. 全链路测试

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT=$(dirname "$(readlink -f "$0")")
cd "$PROJECT_ROOT"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     🚀 Kylin-TARS GUI Agent 全链路联调启动脚本                ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检查参数
MOCK_MODE=false
if [ "$1" == "--mock" ]; then
    MOCK_MODE=true
    echo -e "${YELLOW}📢 模拟模式已启用（无需D-Bus）${NC}"
fi

# 检查Python环境
echo -e "\n${GREEN}[Step 0] 环境检查${NC}"
echo "----------------------------------------"

if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

echo "Python: $($PYTHON_CMD --version)"
echo "工作目录: $PROJECT_ROOT"

# 检查依赖
echo -e "\n检查关键依赖..."
$PYTHON_CMD -c "import json5; print('  ✓ json5')" 2>/dev/null || echo "  ✗ json5 (pip install json5)"
$PYTHON_CMD -c "import fuzzywuzzy; print('  ✓ fuzzywuzzy')" 2>/dev/null || echo "  ✗ fuzzywuzzy (pip install fuzzywuzzy python-Levenshtein)"

if [ "$MOCK_MODE" = false ]; then
    $PYTHON_CMD -c "import dbus; print('  ✓ dbus-python')" 2>/dev/null || echo "  ✗ dbus-python (pip install dbus-python)"
    $PYTHON_CMD -c "from gi.repository import GLib; print('  ✓ PyGObject')" 2>/dev/null || echo "  ✗ PyGObject (pip install PyGObject)"
fi

if [ "$MOCK_MODE" = true ]; then
    # 模拟模式 - 直接运行全链路测试
    echo -e "\n${GREEN}[Step 1] 运行模拟模式全链路测试${NC}"
    echo "----------------------------------------"
    
    $PYTHON_CMD "$PROJECT_ROOT/full_integration.py"
    
    echo -e "\n${GREEN}✓ 模拟模式测试完成!${NC}"
    exit 0
fi

# 完整模式 - 需要D-Bus
echo -e "\n${GREEN}[Step 1] 启动 MCP Server${NC}"
echo "----------------------------------------"

MCP_SERVER_SCRIPT="$PROJECT_ROOT/mcp_system/mcp_server/mcp_server.py"

if [ ! -f "$MCP_SERVER_SCRIPT" ]; then
    echo -e "${RED}❌ MCP Server 脚本不存在: $MCP_SERVER_SCRIPT${NC}"
    exit 1
fi

# 检测当前 conda 环境
CONDA_ENV_NAME="${CONDA_DEFAULT_ENV:-}"
CONDA_PREFIX_PATH="${CONDA_PREFIX:-}"

echo "当前 Conda 环境: $CONDA_ENV_NAME"
echo "正在后台启动 MCP Server..."

# 保存当前完整的 PATH（包含conda环境）
FULL_PATH="$PATH"
PYTHON_EXEC="$(which python)"

# 在新的D-Bus会话中启动
dbus-run-session -- /bin/bash -c "
    # 恢复完整的 PATH
    export PATH='$FULL_PATH'
    
    # 启动 MCP Server
    '$PYTHON_EXEC' '$MCP_SERVER_SCRIPT' &
    MCP_PID=\$!
    echo \"MCP Server PID: \$MCP_PID\"
    /bin/sleep 3
    
    # 检查是否启动成功
    if /bin/ps -p \$MCP_PID > /dev/null 2>&1; then
        echo '✓ MCP Server 启动成功'
    else
        echo '❌ MCP Server 启动失败'
        exit 1
    fi
    
    # 注册子智能体
    echo ''
    echo '[Step 2] 注册子智能体'
    echo '----------------------------------------'
    '$PYTHON_EXEC' '$PROJECT_ROOT/agent_register.py'
    
    # 运行全链路测试
    echo ''
    echo '[Step 3] 运行全链路测试'
    echo '----------------------------------------'
    '$PYTHON_EXEC' '$PROJECT_ROOT/full_integration.py'
    
    # 停止 MCP Server
    echo ''
    echo '[Step 4] 清理'
    echo '----------------------------------------'
    /bin/kill \$MCP_PID 2>/dev/null || true
    echo '✓ MCP Server 已停止'
"

echo -e "\n${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                   ✓ 联调测试完成!                            ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"

