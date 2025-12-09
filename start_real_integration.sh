#!/bin/bash
# Kylin-TARS GUI Agent 真实联调启动脚本
#
# 本脚本启动真实的子智能体服务，进行真实的系统操作
#
# 使用方式：
#   ./start_real_integration.sh
#
# 启动顺序：
#   1. MCP Server (成员A)
#   2. FileAgent 服务 (成员C)
#   3. SettingsAgent 服务 (成员C)
#   4. Gradio 前端界面 (成员C)

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT=$(dirname "$(readlink -f "$0")")
cd "$PROJECT_ROOT"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  🚀 Kylin-TARS GUI Agent 真实联调启动脚本                    ║${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}║  ⚠️  本脚本将进行真实的系统操作！                            ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 保存环境
FULL_PATH="$PATH"
PYTHON_EXEC="$(which python)"

echo -e "${GREEN}[环境信息]${NC}"
echo "Python: $PYTHON_EXEC"
echo "Conda环境: ${CONDA_DEFAULT_ENV:-未激活}"
echo "工作目录: $PROJECT_ROOT"
echo ""

# 检查成员C的子智能体代码
AGENT_DIR="$PROJECT_ROOT/Desktop/agent_project/src"
if [ ! -d "$AGENT_DIR" ]; then
    echo -e "${RED}❌ 子智能体代码目录不存在: $AGENT_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}[启动说明]${NC}"
echo "本脚本将启动以下服务："
echo "  1. MCP Server (D-Bus Master Agent)"
echo "  2. FileAgent (文件操作服务)"
echo "  3. SettingsAgent (系统设置服务)"
echo "  4. Gradio UI (Web 界面，端口 7870)"
echo ""
# 移除交互式确认，直接启动
echo -e "${YELLOW}开始启动服务...${NC}"

# 在D-Bus会话中启动所有服务
dbus-run-session -- /bin/bash -c "
    export PATH='$FULL_PATH'
    
    echo ''
    echo '=========================================='
    echo '[Step 1] 启动 MCP Server'
    echo '=========================================='
    
    '$PYTHON_EXEC' '$PROJECT_ROOT/mcp_system/mcp_server/mcp_server_fixed.py' &
    MCP_PID=\$!
    echo \"MCP Server PID: \$MCP_PID\"
    /bin/sleep 2
    
    if /bin/ps -p \$MCP_PID > /dev/null 2>&1; then
        echo '✓ MCP Server 启动成功'
    else
        echo '❌ MCP Server 启动失败'
        exit 1
    fi
    
    echo ''
    echo '=========================================='
    echo '[Step 2] 启动 FileAgent 服务'
    echo '=========================================='
    
    cd '$AGENT_DIR'
    '$PYTHON_EXEC' file_agent_mcp.py &
    FILE_AGENT_PID=\$!
    echo \"FileAgent PID: \$FILE_AGENT_PID\"
    /bin/sleep 2
    
    echo ''
    echo '=========================================='
    echo '[Step 3] 启动 SettingsAgent 服务'
    echo '=========================================='
    
    '$PYTHON_EXEC' settings_agent_mcp.py &
    SETTINGS_AGENT_PID=\$!
    echo \"SettingsAgent PID: \$SETTINGS_AGENT_PID\"
    /bin/sleep 2
    
    echo ''
    echo '=========================================='
    echo '[Step 4] 启动 Gradio UI'
    echo '=========================================='
    
    echo '正在启动 Gradio 界面...'
    echo '访问地址: http://localhost:7860'
    echo ''
    echo -e '${YELLOW}按 Ctrl+C 停止所有服务${NC}'
    
    '$PYTHON_EXEC' gradio_ui.py
    
    # 清理
    /bin/kill \$MCP_PID \$FILE_AGENT_PID \$SETTINGS_AGENT_PID 2>/dev/null || true
"

echo ""
echo -e "${GREEN}✓ 所有服务已停止${NC}"

