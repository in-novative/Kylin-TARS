#!/bin/bash
# Kylin-TARS 升级版功能测试脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  🧪 Kylin-TARS 升级版功能测试                               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 项目根目录
PROJECT_ROOT=$(dirname "$(readlink -f "$0")")
cd "$PROJECT_ROOT"

# 激活环境
source /data0/miniconda3/etc/profile.d/conda.sh
conda activate uitars-vllm

# 测试目录
TEST_DIR="$PROJECT_ROOT/Desktop/agent_project/src"

echo -e "${YELLOW}[1/6] 测试 FileAgent 逻辑...${NC}"
python3 -c "
from file_agent_logic import FileAgentLogic
agent = FileAgentLogic()
result = agent.search_file('$HOME/Downloads', '.png', recursive=False)
print(f'  ✓ FileAgent 测试通过: {result[\"status\"]}')
" || echo "  ✗ FileAgent 测试失败"

echo ""
echo -e "${YELLOW}[2/6] 测试 SettingsAgent 逻辑...${NC}"
python3 -c "
from settings_agent_logic import SettingsAgentLogic
agent = SettingsAgentLogic()
result = agent.get_volume()
print(f'  ✓ SettingsAgent 测试通过: {result[\"status\"]}')
" || echo "  ✗ SettingsAgent 测试失败"

echo ""
echo -e "${YELLOW}[3/6] 测试 NetworkAgent 逻辑...${NC}"
python3 -c "
from network_agent_logic import NetworkAgentLogic
agent = NetworkAgentLogic()
result = agent.get_network_status()
print(f'  ✓ NetworkAgent 测试通过: {result[\"status\"]}')
" || echo "  ✗ NetworkAgent 测试失败"

echo ""
echo -e "${YELLOW}[4/6] 测试 AppAgent 逻辑...${NC}"
python3 -c "
from app_agent_logic import AppAgentLogic
agent = AppAgentLogic()
result = agent.list_running_apps()
print(f'  ✓ AppAgent 测试通过: {result[\"status\"]}')
" || echo "  ✗ AppAgent 测试失败"

echo ""
echo -e "${YELLOW}[5/6] 检查 Gradio UI 文件...${NC}"
if [ -f "$TEST_DIR/gradio_upgrade.py" ]; then
    echo "  ✓ gradio_upgrade.py 存在"
    python3 -c "
import sys
sys.path.insert(0, '$TEST_DIR')
try:
    import gradio_upgrade
    print('  ✓ Gradio UI 模块导入成功')
except Exception as e:
    print(f'  ✗ Gradio UI 导入失败: {e}')
" || echo "  ✗ Gradio UI 检查失败"
else
    echo "  ✗ gradio_upgrade.py 不存在"
fi

echo ""
echo -e "${YELLOW}[6/6] 检查启动脚本...${NC}"
if [ -f "$PROJECT_ROOT/start_upgrade.sh" ]; then
    echo "  ✓ start_upgrade.sh 存在"
    if [ -x "$PROJECT_ROOT/start_upgrade.sh" ]; then
        echo "  ✓ 启动脚本可执行"
    else
        echo "  ⚠ 启动脚本不可执行，运行: chmod +x start_upgrade.sh"
    fi
else
    echo "  ✗ start_upgrade.sh 不存在"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ 功能测试完成                                             ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║  启动升级版系统:                                            ║${NC}"
echo -e "${GREEN}║    ./start_upgrade.sh                                       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"

