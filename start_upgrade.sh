#!/bin/bash
# Kylin-TARS GUI Agent 升级版启动脚本
#
# 包含6个智能体：
#   - FileAgent: 文件操作
#   - SettingsAgent: 系统设置
#   - NetworkAgent: 网络管理
#   - AppAgent: 应用管理
#   - MonitorAgent: 系统监控
#   - MediaAgent: 媒体控制
#
# 使用方式：
#   ./start_upgrade.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT=$(dirname "$(readlink -f "$0")")
cd "$PROJECT_ROOT"

# 加载 API 配置（如果存在）
CONFIG_DIR="$HOME/.config/kylin-gui-agent"
if [ -f "$CONFIG_DIR/api_config.sh" ]; then
    echo -e "${CYAN}[加载API配置]${NC}"
    source "$CONFIG_DIR/api_config.sh"
    echo "  API地址: ${VLLM_API_BASE:-未设置}"
fi

# 设置默认值
export VLLM_API_BASE="${VLLM_API_BASE:-http://localhost:8000}"
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/mcp_system:$PROJECT_ROOT/Desktop/agent_project:$PYTHONPATH"

echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║                                                              ║${NC}"
echo -e "${PURPLE}║  🚀 Kylin-TARS GUI Agent 升级版                              ║${NC}"
echo -e "${PURPLE}║                                                              ║${NC}"
echo -e "${PURPLE}║  智能体: FileAgent | SettingsAgent | NetworkAgent | AppAgent | MonitorAgent | MediaAgent ║${NC}"
echo -e "${PURPLE}║                                                              ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 保存环境
FULL_PATH="$PATH"
PYTHON_EXEC="$(which python)"

echo -e "${CYAN}[环境信息]${NC}"
echo "  Python: $PYTHON_EXEC"
echo "  Conda环境: ${CONDA_DEFAULT_ENV:-未激活}"
echo "  工作目录: $PROJECT_ROOT"
echo ""

# 子智能体目录
AGENT_DIR="$PROJECT_ROOT/Desktop/agent_project/src"

echo -e "${YELLOW}开始启动服务...${NC}"
echo ""

# 在 D-Bus 会话中启动所有服务
dbus-run-session -- /bin/bash -c "
    export PATH='$FULL_PATH'
    
    echo -e '${GREEN}[1/6] 启动 MCP Server${NC}'
    '$PYTHON_EXEC' '$PROJECT_ROOT/mcp_system/mcp_server/mcp_server.py' &
    MCP_PID=\$!
    /bin/sleep 3
    
    if /bin/ps -p \$MCP_PID > /dev/null 2>&1; then
        echo '  ✓ MCP Server 启动成功'
    else
        echo '  ✗ MCP Server 启动失败'
        exit 1
    fi
    
    echo ''
    echo -e '${GREEN}[2/6] 启动 FileAgent${NC}'
    cd '$AGENT_DIR'
    '$PYTHON_EXEC' file_agent_mcp.py &
    /bin/sleep 1
    echo '  ✓ FileAgent 已启动'
    
    echo ''
    echo -e '${GREEN}[3/6] 启动 SettingsAgent${NC}'
    '$PYTHON_EXEC' settings_agent_mcp.py &
    /bin/sleep 1
    echo '  ✓ SettingsAgent 已启动'
    
    echo ''
    echo -e '${GREEN}[4/6] 启动 NetworkAgent${NC}'
    '$PYTHON_EXEC' network_agent_mcp.py &
    /bin/sleep 1
    echo '  ✓ NetworkAgent 已启动'
    
    echo ''
    echo -e '${GREEN}[5/7] 启动 AppAgent${NC}'
    '$PYTHON_EXEC' app_agent_mcp.py &
    /bin/sleep 1
    echo '  ✓ AppAgent 已启动'
    
    echo ''
    echo -e '${GREEN}[6/7] 启动 MonitorAgent${NC}'
    '$PYTHON_EXEC' monitor_agent_mcp.py &
    /bin/sleep 1
    echo '  ✓ MonitorAgent 已启动'
    
    echo ''
    echo -e '${GREEN}[7/7] 启动 MediaAgent${NC}'
    '$PYTHON_EXEC' media_agent_mcp.py &
    /bin/sleep 1
    echo '  ✓ MediaAgent 已启动'
    
    echo ''
    echo -e '${GREEN}[8/8] 启动 Gradio UI（升级版）${NC}'
    echo ''
    echo -e '${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}'
    echo -e '${PURPLE}║  ✓ 所有服务启动成功！                                        ║${NC}'
    echo -e '${PURPLE}║                                                              ║${NC}'
    echo -e '${PURPLE}║  🌐 Web UI: http://localhost:7870                            ║${NC}'
    echo -e '${PURPLE}║                                                              ║${NC}'
    echo -e '${PURPLE}║  已注册智能体:                                               ║${NC}'
    echo -e '${PURPLE}║    • FileAgent     - 文件搜索、移动到回收站                  ║${NC}'
    echo -e '${PURPLE}║    • SettingsAgent - 壁纸设置、音量调整、蓝牙管理            ║${NC}'
    echo -e '${PURPLE}║    • NetworkAgent  - WiFi连接、代理设置、网络测速            ║${NC}'
    echo -e '${PURPLE}║    • AppAgent      - 应用启动、关闭、快捷操作                ║${NC}'
    echo -e '${PURPLE}║    • MonitorAgent  - 系统监控、进程清理                      ║${NC}'
    echo -e '${PURPLE}║    • MediaAgent    - 媒体播放、控制                          ║${NC}'
    echo -e '${PURPLE}║                                                              ║${NC}'
    echo -e '${PURPLE}║  按 Ctrl+C 停止所有服务                                      ║${NC}'
    echo -e '${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}'
    echo ''
    
    '$PYTHON_EXEC' gradio_upgrade.py
    
    /bin/kill \$MCP_PID 2>/dev/null || true
"

echo ""
echo -e "${GREEN}✓ 所有服务已停止${NC}"

