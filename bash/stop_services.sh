#!/bin/bash
# 停止所有 Kylin-TARS 相关服务

echo "🛑 停止 Kylin-TARS 服务..."
echo ""

# 杀死进程
pkill -f "gradio_ui" 2>/dev/null && echo "✓ Gradio UI 已停止" || echo "○ Gradio UI 未运行"
pkill -f "mcp_server" 2>/dev/null && echo "✓ MCP Server 已停止" || echo "○ MCP Server 未运行"
pkill -f "file_agent_mcp" 2>/dev/null && echo "✓ FileAgent 已停止" || echo "○ FileAgent 未运行"
pkill -f "settings_agent_mcp" 2>/dev/null && echo "✓ SettingsAgent 已停止" || echo "○ SettingsAgent 未运行"

# 释放端口
fuser -k 7870/tcp 2>/dev/null
fuser -k 7860/tcp 2>/dev/null

sleep 1
echo ""
echo "✓ 清理完成"

