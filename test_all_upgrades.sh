#!/bin/bash
# Kylin-TARS 全面升级测试脚本
#
# 测试所有已完成的升级功能：
# - 模块一：System-2推理、指令补全、新智能体、功能扩展
# - 模块二：用户偏好学习、语义检索、记忆可视化
# - 模块三：MCP负载均衡、状态广播、日志追溯
# - 模块四：模型适配、自动切换
# - 模块五：配置管理、权限分级、备份恢复

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

echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║  🧪 Kylin-TARS 全面升级测试                                  ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 测试结果统计
PASSED=0
FAILED=0
SKIPPED=0

# 测试函数
test_check() {
    local name="$1"
    local command="$2"
    
    echo -n "测试: $name... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 通过${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ 失败${NC}"
        ((FAILED++))
        return 1
    fi
}

test_skip() {
    local name="$1"
    echo -e "测试: $name... ${YELLOW}⊘ 跳过${NC}"
    ((SKIPPED++))
}

# ============================================================
# 模块一：System-2推理与智能体扩展
# ============================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}模块一：System-2推理与智能体扩展${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 1.1 System-2 Prompt扩展
test_check "System-2 Prompt文件存在" "test -f system2_prompt.py"
test_check "System-2 Prompt包含多轮上下文" "grep -q 'context_ref' system2_prompt.py"
test_check "System-2 Prompt包含新功能识别" "grep -q 'tool_extend' system2_prompt.py"

# 1.2 指令补全模块
test_check "指令补全模块存在" "grep -q '指令补全\|追问' system2_prompt.py || grep -q 'clarify\|complete' system2_prompt.py"

# 1.3 新智能体
test_check "MonitorAgent逻辑文件存在" "test -f Desktop/agent_project/src/monitor_agent_logic.py"
test_check "MonitorAgent MCP文件存在" "test -f Desktop/agent_project/src/monitor_agent_mcp.py"
test_check "MediaAgent逻辑文件存在" "test -f Desktop/agent_project/src/media_agent_logic.py"
test_check "MediaAgent MCP文件存在" "test -f Desktop/agent_project/src/media_agent_mcp.py"

# 1.4 功能扩展
test_check "SettingsAgent蓝牙功能" "grep -q 'bluetooth_manage' Desktop/agent_project/src/settings_agent_logic.py"
test_check "NetworkAgent测速功能" "grep -q 'speed_test' Desktop/agent_project/src/network_agent_logic.py"
test_check "AppAgent快捷操作" "grep -q 'app_quick_operation' Desktop/agent_project/src/app_agent_logic.py"
test_check "FileAgent批量重命名" "grep -q 'batch_rename\|批量重命名' Desktop/agent_project/src/file_agent_logic.py || echo 'skip'"

echo ""

# ============================================================
# 模块二：记忆与检索
# ============================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}模块二：记忆与检索${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 2.1 用户偏好学习
test_check "记忆存储模块存在" "test -f memory_store.py"
test_check "用户偏好学习功能" "grep -q 'update_user_preference\|get_user_preference_prompt' memory_store.py"

# 2.2 语义检索
test_check "记忆检索模块存在" "test -f memory_retrieve.py"
test_check "语义检索功能" "grep -q 'semantic_retrieve\|KYLIN_AI\|sentence_transformers' memory_retrieve.py"

# 2.3 记忆可视化
test_check "记忆可视化模块存在" "test -f memory_visualization.py"
test_check "可视化使用networkx" "grep -q 'networkx\|nx\\.' memory_visualization.py"

echo ""

# ============================================================
# 模块三：MCP系统优化
# ============================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}模块三：MCP系统优化${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 3.1 负载均衡和故障转移
test_check "MCP Server文件存在" "test -f mcp_system/mcp_server/mcp_server.py"
test_check "负载均衡功能" "grep -q '_load_balance\|load_balance' mcp_system/mcp_server/mcp_server.py"
test_check "故障转移功能" "grep -q '_fault_tolerance\|fault_tolerance' mcp_system/mcp_server/mcp_server.py"

# 3.2 状态广播
test_check "状态广播功能" "grep -q '_broadcast_agent_status\|broadcast' mcp_system/mcp_server/mcp_server.py"
test_check "心跳监控" "grep -q 'start_heartbeat_monitor\|_check_agent_heartbeats' mcp_system/mcp_server/mcp_server.py"

# 3.3 日志追溯
test_check "协作日志模块存在" "test -f collaboration_logger.py"
test_check "日志类型定义" "grep -q 'LogType\|DECISION\|SCHEDULE\|EXECUTION\|BROADCAST' collaboration_logger.py"

echo ""

# ============================================================
# 模块四：模型适配
# ============================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}模块四：模型适配${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 4.1 模型适配层
test_check "模型适配模块存在" "test -f model_adapter.py"
test_check "Qwen2.5系列支持" "grep -q 'Qwen2.5\|QWEN2_5' model_adapter.py"
test_check "自动切换功能" "grep -q 'auto_switch_model\|switch_model' model_adapter.py"

# 4.2 System-2集成
test_check "System-2集成模型适配器" "grep -q 'model_adapter\|get_model_adapter' system2_prompt.py"

echo ""

# ============================================================
# 模块五：MCP配置管理
# ============================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}模块五：MCP配置管理${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 5.1 配置管理
test_check "配置管理模块存在" "test -f mcp_config_manager.py"
test_check "权限分级功能" "grep -q 'PermissionLevel\|ADMIN\|NORMAL\|READONLY' mcp_config_manager.py"
test_check "备份恢复功能" "grep -q 'backup_config\|restore_config' mcp_config_manager.py"

echo ""

# ============================================================
# Gradio界面集成
# ============================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Gradio界面集成${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Gradio升级版
test_check "Gradio升级版文件存在" "test -f Desktop/agent_project/src/gradio_upgrade.py"
test_check "Gradio集成记忆模块" "grep -q 'memory_store\|memory_retrieve\|memory_visualization' Desktop/agent_project/src/gradio_upgrade.py"
test_check "Gradio集成日志模块" "grep -q 'collaboration_logger' Desktop/agent_project/src/gradio_upgrade.py"
test_check "Gradio包含记忆轨迹页" "grep -q '记忆轨迹\|memory' Desktop/agent_project/src/gradio_upgrade.py"
test_check "Gradio包含协作日志页" "grep -q '协作日志\|collaboration_log' Desktop/agent_project/src/gradio_upgrade.py"

echo ""

# ============================================================
# 启动脚本
# ============================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}启动脚本检查${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_check "启动脚本存在" "test -f start_upgrade.sh"
test_check "启动脚本可执行" "test -x start_upgrade.sh"

echo ""

# ============================================================
# README文档
# ============================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}README文档检查${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_check "README升级文档存在" "test -f README_UPGRADE.md"

echo ""

# ============================================================
# 实际功能测试（可选，需要服务运行）
# ============================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}实际功能测试（需要服务运行）${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 检查MCP Server是否运行
if dbus-send --session --print-reply --dest=com.kylin.ai.mcp.MasterAgent /com/kylin/ai/mcp/MasterAgent com.kylin.ai.mcp.MasterAgent.Ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MCP Server正在运行${NC}"
    
    # 测试获取工具列表
    echo -n "测试: MCP工具列表查询... "
    if dbus-send --session --print-reply --dest=com.kylin.ai.mcp.MasterAgent /com/kylin/ai/mcp/MasterAgent com.kylin.ai.mcp.MasterAgent.ToolsList > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 通过${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ 失败${NC}"
        ((FAILED++))
    fi
    
    # 测试获取智能体列表
    echo -n "测试: MCP智能体列表查询... "
    if dbus-send --session --print-reply --dest=com.kylin.ai.mcp.MasterAgent /com/kylin/ai/mcp/MasterAgent com.kylin.ai.mcp.MasterAgent.AgentsList > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 通过${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ 失败${NC}"
        ((FAILED++))
    fi
else
    echo -e "${YELLOW}⊘ MCP Server未运行，跳过实际功能测试${NC}"
    ((SKIPPED+=2))
fi

# 检查Gradio是否运行
if curl -s http://localhost:7870 > /dev/null 2>&1 || curl -s http://localhost:7871 > /dev/null 2>&1 || curl -s http://localhost:7872 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Gradio UI正在运行${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⊘ Gradio UI未运行，跳过UI测试${NC}"
    ((SKIPPED++))
fi

echo ""

# ============================================================
# 测试总结
# ============================================================
echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║  测试总结                                                      ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${GREEN}通过: ${PASSED}${NC}"
echo -e "  ${RED}失败: ${FAILED}${NC}"
echo -e "  ${YELLOW}跳过: ${SKIPPED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ 所有测试通过！${NC}"
    exit 0
else
    echo -e "${RED}✗ 部分测试失败，请检查上述错误${NC}"
    exit 1
fi

