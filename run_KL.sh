#!/bin/bash
# Kylin-TARS GUI Agent 升级版启动脚本（Kylin 虚拟机专用）
#
# 适配 Kylin 虚拟机环境的启动脚本，包含：
#   - 更详细的错误处理和日志输出
#   - 环境检查（图形界面、DBus、Python 模块）
#   - 进程状态监控
#   - 优雅的错误恢复机制
#
# 包含6个智能体：
#   - FileAgent: 文件操作
#   - SettingsAgent: 系统设置
#   - NetworkAgent: 网络管理
#   - AppAgent: 应用管理
#   - MonitorAgent: 系统监控
#   - MediaAgent: 媒体控制

# 这对于openKylin系统很重要，因为PyGObject通过系统包python3-gi提供
export PYTHONPATH="/usr/lib/python3/dist-packages:$PYTHONPATH"
export GI_TYPELIB_PATH="/usr/lib/x86_64-linux-gnu/girepository-1.0:/usr/share/gir-1.0:$GI_TYPELIB_PATH"
export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"

# 使用外部大模型 API
export UITARS_API_BASE="https://xiaoai.plus/v1"
export VLLM_MODEL_NAME="gpt-4o"

# 如果需要 API Key
export OPENAI_API_KEY="sk-lgW2a38mNKdL3lAfKnjQ55yl3NujlfAwlg7u6GqjOfJXyOKU"

# 不使用 set -e，以便捕获和处理错误
set +e

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

# 日志目录
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"
STARTUP_LOG="$LOG_DIR/startup_$(date +%Y%m%d_%H%M%S).log"

# 日志函数
log_info() {
    echo -e "${CYAN}[INFO]${NC} $1" | tee -a "$STARTUP_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$STARTUP_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$STARTUP_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$STARTUP_LOG"
}

# 错误处理函数
handle_error() {
    local exit_code=$?
    local line_number=$1
    log_error "脚本在第 $line_number 行发生错误，退出码: $exit_code"
    log_error "请查看日志文件: $STARTUP_LOG"
    exit $exit_code
}

# 设置错误陷阱
trap 'handle_error $LINENO' ERR

echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║                                                              ║${NC}"
echo -e "${PURPLE}║  🚀 Kylin-TARS GUI Agent 升级版                              ║${NC}"
echo -e "${PURPLE}║                                                              ║${NC}"
echo -e "${PURPLE}║  智能体: FileAgent | SettingsAgent | NetworkAgent | AppAgent | MonitorAgent | MediaAgent ║${NC}"
echo -e "${PURPLE}║                                                              ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 静默环境检查（只在失败时输出）
# 检查图形界面环境（GUI环境，不是虚拟环境）
# 注意：这是检查图形界面（DISPLAY/WAYLAND），不是检查Python虚拟环境（venv）
if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]; then
    # 尝试设置默认 DISPLAY（如果可能）
    if [ -S /tmp/.X11-unix/X0 ] 2>/dev/null; then
        export DISPLAY=:0
        echo -e "${GREEN}[信息] 自动设置 DISPLAY=:0${NC}" | tee -a "$STARTUP_LOG"
    elif command -v loginctl >/dev/null 2>&1; then
        # 尝试从 systemd 获取活动的图形会话
        ACTIVE_SESSION=$(loginctl list-sessions --no-legend 2>/dev/null | grep -E 'seat0|graphical' | head -1 | awk '{print $1}')
        if [ -n "$ACTIVE_SESSION" ]; then
            export DISPLAY=$(loginctl show-session "$ACTIVE_SESSION" -p Display 2>/dev/null | cut -d= -f2)
            if [ -n "$DISPLAY" ]; then
                echo -e "${GREEN}[信息] 从 systemd 会话获取 DISPLAY=$DISPLAY${NC}" | tee -a "$STARTUP_LOG"
            fi
        fi
    fi
    
    # 如果仍然没有设置，显示警告
    if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]; then
        echo -e "${YELLOW}[警告] 未检测到图形界面环境（DISPLAY/WAYLAND），某些GUI功能可能不可用${NC}" | tee -a "$STARTUP_LOG"
        echo -e "${YELLOW}      注意：这是检查图形界面环境，不是检查Python虚拟环境${NC}" | tee -a "$STARTUP_LOG"
    fi
fi

# 检查 Python
PYTHON_EXEC="$(which python3 2>/dev/null || which python 2>/dev/null)"
if [ -z "$PYTHON_EXEC" ]; then
    echo -e "${RED}[错误] 未找到 Python 解释器${NC}" | tee -a "$STARTUP_LOG"
    exit 1
fi

# 检查必要的 Python 模块
MISSING_MODULES=()
REQUIRED_MODULES=("dbus" "gradio" "gi" "psutil" "requests" "matplotlib" "networkx" "openai")

for module in "${REQUIRED_MODULES[@]}"; do
    if ! $PYTHON_EXEC -c "import $module" 2>/dev/null; then
        MISSING_MODULES+=("$module")
    fi
done

if [ ${#MISSING_MODULES[@]} -gt 0 ]; then
    echo -e "${RED}[错误] 缺少必要的 Python 模块: ${MISSING_MODULES[*]}${NC}" | tee -a "$STARTUP_LOG"
    echo -e "${YELLOW}请按照 VM_ENVIRONMENT_SETUP.md 配置环境${NC}" | tee -a "$STARTUP_LOG"
    exit 1
fi

# 检查 DBus
if ! command -v dbus-run-session &> /dev/null; then
    echo -e "${RED}[错误] 未找到 dbus-run-session 命令${NC}" | tee -a "$STARTUP_LOG"
    exit 1
fi

# 检查项目文件
REQUIRED_FILES=(
    "mcp_system/mcp_server/mcp_server.py"
    "desktop/agent_project/src/gradio_upgrade.py"
    "desktop/agent_project/src/file_agent_mcp.py"
    "desktop/agent_project/src/settings_agent_mcp.py"
    "desktop/agent_project/src/network_agent_mcp.py"
    "desktop/agent_project/src/app_agent_mcp.py"
    "desktop/agent_project/src/monitor_agent_mcp.py"
    "desktop/agent_project/src/media_agent_mcp.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$PROJECT_ROOT/$file" ]; then
        echo -e "${RED}[错误] 缺少必要文件: $file${NC}" | tee -a "$STARTUP_LOG"
        exit 1
    fi
done

# 加载 API 配置（如果存在）
CONFIG_DIR="$HOME/.config/kylin-gui-agent"
if [ -f "$CONFIG_DIR/api_config.sh" ]; then
    source "$CONFIG_DIR/api_config.sh"
fi

# 设置默认值（虚拟机环境使用远程UITARS API）
export VLLM_API_BASE="${VLLM_API_BASE:-http://localhost:8000}"
export UITARS_API_BASE="${UITARS_API_BASE:-${VLLM_API_BASE}}"

# API Key 配置（支持多个环境变量名）
export UITARS_API_KEY="${UITARS_API_KEY:-${OPENAI_API_KEY:-${API_KEY:-}}}"

# 模型名称配置（外部API使用模型名称，本地vLLM使用模型路径）
if [ -n "$UITARS_API_BASE" ] && [ "$UITARS_API_BASE" != "http://localhost:8000" ]; then
    # 外部API：使用模型名称
    export UITARS_MODEL_NAME="${UITARS_MODEL_NAME:-${VLLM_MODEL_NAME:-gpt-4o}}"
else
    # 本地vLLM：使用模型路径
    export VLLM_MODEL_NAME="${VLLM_MODEL_NAME:-/data1/models/UI-TARS-1.5-7B}"
fi

# 检查UITARS_API_BASE是否配置（记忆模块需要）
if [ -z "$UITARS_API_BASE" ] || [ "$UITARS_API_BASE" = "http://localhost:8000" ]; then
    echo -e "${YELLOW}[警告] UITARS_API_BASE 未正确配置，记忆模块将无法使用${NC}" | tee -a "$STARTUP_LOG"
    echo -e "${YELLOW}请设置环境变量: export UITARS_API_BASE=\"http://YOUR_SERVER_IP:8000\"${NC}" | tee -a "$STARTUP_LOG"
    echo -e "${YELLOW}或创建配置文件: ~/.config/kylin-gui-agent/api_config.sh${NC}" | tee -a "$STARTUP_LOG"
    echo ""
fi

# 检查API Key是否配置（外部API需要）
if [ -n "$UITARS_API_BASE" ] && [ "$UITARS_API_BASE" != "http://localhost:8000" ] && [ -z "$UITARS_API_KEY" ]; then
    echo -e "${YELLOW}[警告] UITARS_API_KEY 未配置，外部API调用可能失败（401错误）${NC}" | tee -a "$STARTUP_LOG"
    echo -e "${YELLOW}请设置环境变量: export UITARS_API_KEY=\"your-api-key\"${NC}" | tee -a "$STARTUP_LOG"
    echo ""
fi

# 设置 PYTHONPATH，包含所有必要的模块目录
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/mcp_system:$PROJECT_ROOT/desktop/agent_project:$PROJECT_ROOT/run:$PROJECT_ROOT/memory:$PROJECT_ROOT/log:$PYTHONPATH"

# 设置Python环境变量，使虚拟环境能够访问系统包（特别是PyGObject）
# 这对于openKylin系统很重要，因为PyGObject通过系统包python3-gi提供
# 注意：这些路径需要根据实际系统架构调整（x86_64 或 aarch64）
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
export GI_TYPELIB_PATH="$GI_LIB_PATH:/usr/share/gir-1.0:${GI_TYPELIB_PATH:-}"
export LD_LIBRARY_PATH="$LD_LIB_PATH:${LD_LIBRARY_PATH:-}"

# 设置UITARS API地址（如果未设置，则使用VLLM_API_BASE）
export UITARS_API_BASE="${UITARS_API_BASE:-}"

# 设置D-Bus系统总线地址，蓝牙服务需要使用
export DBUS_SYSTEM_BUS_ADDRESS=unix:path=/var/run/dbus/system_bus_socket

# 保存环境
FULL_PATH="$PATH"

# 子智能体目录
AGENT_DIR="$PROJECT_ROOT/desktop/agent_project/src"

echo -e "${CYAN}[环境信息]${NC}"
echo "  Python: $PYTHON_EXEC"
echo "  Conda环境: ${CONDA_DEFAULT_ENV:-未激活}"
echo "  工作目录: $PROJECT_ROOT"
if [ -n "$UITARS_API_BASE" ] && [ "$UITARS_API_BASE" != "http://localhost:8000" ]; then
    echo "  UITARS_API_BASE: $UITARS_API_BASE (远程API)"
else
    echo "  UITARS_API_BASE: 未设置（记忆模块不可用）"
fi
echo ""

echo -e "${YELLOW}开始启动服务...${NC}"
echo ""
echo -e "${CYAN}[环境配置]${NC}"
echo "  PYTHONPATH: $PYTHONPATH"
echo "  GI_TYPELIB_PATH: $GI_TYPELIB_PATH"
if [ -n "$UITARS_API_BASE" ] && [ "$UITARS_API_BASE" != "http://localhost:8000" ]; then
    echo "  UITARS_API_BASE: $UITARS_API_BASE (外部API)"
else
    echo "  VLLM_API_BASE: $VLLM_API_BASE (本地vLLM)"
fi
echo ""

# 清理函数
cleanup() {
    log_info "正在清理进程..."
    if [ -n "$MCP_PID" ]; then
        kill "$MCP_PID" 2>/dev/null || true
    fi
    # 清理所有子智能体进程
    pkill -f "file_agent_mcp.py" 2>/dev/null || true
    pkill -f "settings_agent_mcp.py" 2>/dev/null || true
    pkill -f "network_agent_mcp.py" 2>/dev/null || true
    pkill -f "app_agent_mcp.py" 2>/dev/null || true
    pkill -f "monitor_agent_mcp.py" 2>/dev/null || true
    pkill -f "media_agent_mcp.py" 2>/dev/null || true
    log_success "清理完成"
}

# 设置退出陷阱
trap cleanup EXIT INT TERM

# 在 D-Bus 会话中启动所有服务
dbus-run-session -- /bin/bash -c "
    set +e
    export PATH='$FULL_PATH'
    export PYTHONPATH='$PYTHONPATH'
    export GI_TYPELIB_PATH='$GI_TYPELIB_PATH'
    export LD_LIBRARY_PATH='$LD_LIBRARY_PATH'
    export UITARS_API_BASE='$UITARS_API_BASE'
    export VLLM_API_BASE='$VLLM_API_BASE'
    export UITARS_API_KEY='$UITARS_API_KEY'
    export UITARS_MODEL_NAME='$UITARS_MODEL_NAME'
    export VLLM_MODEL_NAME='$VLLM_MODEL_NAME'
    export DISPLAY='${DISPLAY:-}'
    export WAYLAND_DISPLAY='${WAYLAND_DISPLAY:-}'
    export DBUS_SYSTEM_BUS_ADDRESS='unix:path=/var/run/dbus/system_bus_socket'
    
    # 重定向错误到日志
    exec 2>> '$STARTUP_LOG'
    
    echo -e '${GREEN}[1/8] 启动 MCP Server${NC}'
    '$PYTHON_EXEC' '$PROJECT_ROOT/mcp_system/mcp_server/mcp_server.py' >> '$STARTUP_LOG' 2>&1 &
    MCP_PID=\$!
    /bin/sleep 3
    
    if /bin/ps -p \$MCP_PID > /dev/null 2>&1; then
        echo '  ✓ MCP Server 启动成功'
    else
        echo '  ✗ MCP Server 启动失败'
        exit 1
    fi
    
    echo ''
    echo -e '${GREEN}[2/8] 启动 FileAgent${NC}'
    cd '$AGENT_DIR'
    '$PYTHON_EXEC' file_agent_mcp.py >> '$STARTUP_LOG' 2>&1 &
    /bin/sleep 1
    echo '  ✓ FileAgent 已启动'
    
    echo ''
    echo -e '${GREEN}[3/8] 启动 SettingsAgent${NC}'
    '$PYTHON_EXEC' settings_agent_mcp.py >> '$STARTUP_LOG' 2>&1 &
    /bin/sleep 1
    echo '  ✓ SettingsAgent 已启动'
    
    echo ''
    echo -e '${GREEN}[4/8] 启动 NetworkAgent${NC}'
    '$PYTHON_EXEC' network_agent_mcp.py >> '$STARTUP_LOG' 2>&1 &
    /bin/sleep 1
    echo '  ✓ NetworkAgent 已启动'
    
    echo ''
    echo -e '${GREEN}[5/8] 启动 AppAgent${NC}'
    '$PYTHON_EXEC' app_agent_mcp.py >> '$STARTUP_LOG' 2>&1 &
    /bin/sleep 1
    echo '  ✓ AppAgent 已启动'
    
    echo ''
    echo -e '${GREEN}[6/8] 启动 MonitorAgent${NC}'
    '$PYTHON_EXEC' monitor_agent_mcp.py >> '$STARTUP_LOG' 2>&1 &
    /bin/sleep 1
    echo '  ✓ MonitorAgent 已启动'
    
    echo ''
    echo -e '${GREEN}[7/8] 启动 MediaAgent${NC}'
    '$PYTHON_EXEC' media_agent_mcp.py >> '$STARTUP_LOG' 2>&1 &
    /bin/sleep 1
    echo '  ✓ MediaAgent 已启动'
    
    echo ''
    echo -e '${GREEN}[8/8] 启动 Gradio UI（升级版）${NC}'
    echo ''
    echo -e '${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}'
    echo -e '${PURPLE}║  ✓ 所有服务启动成功！                                          ║${NC}'
    echo -e '${PURPLE}║                                                              ║${NC}'
    echo -e '${PURPLE}║  🌐 Web UI: http://localhost:7870                            ║${NC}'
    echo -e '${PURPLE}║                                                              ║${NC}'
    echo -e '${PURPLE}║  已注册智能体:                                                ║${NC}'
    echo -e '${PURPLE}║    • FileAgent     - 文件搜索、移动到回收站                    ║${NC}'
    echo -e '${PURPLE}║    • SettingsAgent - 壁纸设置、音量调整、蓝牙管理              ║${NC}'
    echo -e '${PURPLE}║    • NetworkAgent  - WiFi连接、代理设置、网络测速              ║${NC}'
    echo -e '${PURPLE}║    • AppAgent      - 应用启动、关闭、快捷操作                  ║${NC}'
    echo -e '${PURPLE}║    • MonitorAgent  - 系统监控、进程清理                       ║${NC}'
    echo -e '${PURPLE}║    • MediaAgent    - 媒体播放、控制                           ║${NC}'
    echo -e '${PURPLE}║                                                              ║${NC}'
    echo -e '${PURPLE}║  按 Ctrl+C 停止所有服务                                       ║${NC}'
    echo -e '${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}'
    echo ''
    
    '$PYTHON_EXEC' gradio_upgrade.py
    
    /bin/kill \$MCP_PID 2>/dev/null || true
"

echo ""
echo -e "${GREEN}✓ 所有服务已停止${NC}"

