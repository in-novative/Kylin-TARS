#!/bin/bash
# 准备提交代码到 GitHub

set -e

cd /data1/cyx/Kylin-TARS

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  📦 准备提交代码到 GitHub                                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 1. 检查 Git 状态
echo "[1/5] 检查 Git 状态..."
git status --short

echo ""
echo "[2/5] 添加文件到暂存区..."

# 添加升级版相关文件
git add .gitignore
git add Desktop/agent_project/src/agent_template.py
git add Desktop/agent_project/src/network_agent_logic.py
git add Desktop/agent_project/src/network_agent_mcp.py
git add Desktop/agent_project/src/app_agent_logic.py
git add Desktop/agent_project/src/app_agent_mcp.py
git add Desktop/agent_project/src/gradio_upgrade.py
git add Desktop/agent_project/src/file_agent_mcp.py
git add Desktop/agent_project/src/settings_agent_mcp.py
git add start_upgrade.sh
git add test_upgrade.sh
git add check_ports.sh
git add README_UPGRADE.md

# 添加修改的文件
git add Desktop/agent_project/src/file_agent_mcp.py
git add Desktop/agent_project/src/settings_agent_mcp.py
git add memory_store.py
git add start_real_integration.sh

echo "  ✓ 文件已添加到暂存区"

echo ""
echo "[3/5] 查看将要提交的文件..."
git status --short

echo ""
echo "[4/5] 提交信息预览..."
echo ""
echo "提交信息:"
echo "  feat: 升级版 - 新增 NetworkAgent 和 AppAgent，升级 Gradio UI"
echo ""
echo "主要变更:"
echo "  - ✅ 新增 NetworkAgent（WiFi 和代理管理）"
echo "  - ✅ 新增 AppAgent（应用启动和关闭）"
echo "  - ✅ 升级 Gradio UI（4模块布局 + 交互增强）"
echo "  - ✅ 添加子智能体开发模板"
echo "  - ✅ 实现演示模式和权限控制"
echo "  - ✅ 添加端口检查工具"
echo ""

read -p "是否继续提交？(y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消提交"
    exit 1
fi

echo ""
echo "[5/5] 提交代码..."
git commit -m "feat: 升级版 - 新增 NetworkAgent 和 AppAgent，升级 Gradio UI

主要变更:
- ✅ 新增 NetworkAgent（WiFi 和代理管理）
- ✅ 新增 AppAgent（应用启动和关闭）
- ✅ 升级 Gradio UI（4模块布局 + 交互增强）
- ✅ 添加子智能体开发模板 (agent_template.py)
- ✅ 实现演示模式和权限控制
- ✅ 添加端口检查工具 (check_ports.sh)
- ✅ 完善启动脚本和测试脚本
- ✅ 更新文档 (README_UPGRADE.md)

技术细节:
- NetworkAgent: WiFi 扫描/连接，代理设置（HTTP/HTTPS/SOCKS）
- AppAgent: 应用查找/启动/关闭，运行中应用列表
- Gradio UI: 6个功能模块，历史指令，推理链高亮，实时日志
- 动态端口查找，避免端口冲突"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ✓ 代码已提交到本地仓库                                      ║"
echo "║                                                              ║"
echo "║  下一步：推送到 GitHub                                        ║"
echo "║    git push origin main                                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"

