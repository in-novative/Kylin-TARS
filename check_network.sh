#!/bin/bash
# 网络连接诊断脚本

SERVER_IP="${1:-192.168.153.115}"
SERVER_PORT="${2:-8000}"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  网络连接诊断工具                                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "目标服务器: $SERVER_IP:$SERVER_PORT"
echo ""

# 1. 测试网络连通性
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[1/4] 测试网络连通性 (ping)..."
if ping -c 2 -W 2 "$SERVER_IP" &> /dev/null; then
    echo "   ✅ 可以 ping 通服务器"
    PING_RESULT=$(ping -c 2 -W 2 "$SERVER_IP" 2>&1 | tail -1)
    echo "   $PING_RESULT"
else
    echo "   ❌ 无法 ping 通服务器"
    echo "   ⚠️  建议：检查虚拟机网络模式（应使用桥接模式）"
    echo ""
    echo "   可能的原因："
    echo "   - 虚拟机使用 NAT 模式，无法访问局域网其他主机"
    echo "   - 服务器 IP 地址不正确"
    echo "   - 不在同一网段"
    echo ""
    echo "   解决方案："
    echo "   1. 将虚拟机网络模式改为桥接模式"
    echo "   2. 检查服务器 IP 地址是否正确"
    echo "   3. 确认虚拟机和服务器在同一网络"
    exit 1
fi

# 2. 测试端口连通性
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[2/4] 测试端口连通性 (TCP $SERVER_PORT)..."
if command -v nc &> /dev/null; then
    if nc -zv -w 5 "$SERVER_IP" "$SERVER_PORT" &> /dev/null; then
        echo "   ✅ 端口 $SERVER_PORT 开放"
    else
        echo "   ❌ 端口 $SERVER_PORT 关闭或无法访问"
        echo "   ⚠️  建议：检查服务器服务是否运行和防火墙规则"
        exit 1
    fi
elif timeout 5 bash -c "</dev/tcp/$SERVER_IP/$SERVER_PORT" 2>/dev/null; then
    echo "   ✅ 端口 $SERVER_PORT 开放"
else
    echo "   ❌ 端口 $SERVER_PORT 关闭或无法访问"
    echo "   ⚠️  建议：检查服务器服务是否运行和防火墙规则"
    exit 1
fi

# 3. 测试 HTTP 连接
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[3/4] 测试 HTTP 连接..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
    "http://$SERVER_IP:$SERVER_PORT/health" 2>/dev/null)

if [ -n "$HTTP_CODE" ] && [ "$HTTP_CODE" != "000" ]; then
    echo "   ✅ HTTP 连接成功 (状态码: $HTTP_CODE)"
else
    echo "   ⚠️  HTTP 连接失败（可能服务未运行或路径不存在）"
    echo "   继续测试 API 端点..."
fi

# 4. 测试 API 端点
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[4/4] 测试 API 端点..."
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
    -X POST "http://$SERVER_IP:$SERVER_PORT/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{"model":"test","messages":[{"role":"user","content":"test"}]}' 2>/dev/null)

if [ "$API_RESPONSE" = "200" ]; then
    echo "   ✅ API 服务正常 (HTTP 200)"
elif [ "$API_RESPONSE" = "400" ] || [ "$API_RESPONSE" = "422" ]; then
    echo "   ✅ API 服务可访问 (HTTP $API_RESPONSE - 参数错误，但服务正常)"
elif [ "$API_RESPONSE" = "000" ]; then
    echo "   ❌ API 服务无法连接"
    echo "   ⚠️  可能的原因："
    echo "   - 服务未运行"
    echo "   - 防火墙阻止"
    echo "   - 网络配置问题"
else
    echo "   ⚠️  API 服务响应异常 (HTTP $API_RESPONSE)"
    echo "   建议：检查 API 服务状态和配置"
fi

# 总结
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  诊断完成                                                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

if [ "$API_RESPONSE" = "200" ] || [ "$API_RESPONSE" = "400" ] || [ "$API_RESPONSE" = "422" ]; then
    echo "✅ 网络连接正常，可以配置 UITARS_API_BASE"
    echo ""
    echo "配置命令："
    echo "  export UITARS_API_BASE=\"http://$SERVER_IP:$SERVER_PORT\""
    echo ""
    echo "或创建配置文件："
    echo "  mkdir -p ~/.config/kylin-gui-agent"
    echo "  echo 'export UITARS_API_BASE=\"http://$SERVER_IP:$SERVER_PORT\"' > ~/.config/kylin-gui-agent/api_config.sh"
    echo "  chmod +x ~/.config/kylin-gui-agent/api_config.sh"
else
    echo "❌ 网络连接异常，请按照上述建议排查问题"
fi

