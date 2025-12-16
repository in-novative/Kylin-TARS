#!/bin/bash
# 获取服务器 IP 地址脚本
# 用于确定 vLLM API 服务器的访问地址

echo "=========================================="
echo "服务器 IP 地址查询"
echo "=========================================="
echo ""

# 获取本机 IP 地址（排除回环地址）
echo "📡 本机 IP 地址："
echo "----------------------------------------"

# 方法1：使用 hostname -I（推荐）
if command -v hostname &> /dev/null; then
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    echo "方法1 (hostname -I): $LOCAL_IP"
fi

# 方法2：使用 ip 命令
if command -v ip &> /dev/null; then
    IP_ADDR=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -1)
    if [ -n "$IP_ADDR" ]; then
        echo "方法2 (ip addr):    $IP_ADDR"
    fi
fi

# 方法3：使用 ifconfig
if command -v ifconfig &> /dev/null; then
    IFCONFIG_IP=$(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | head -1)
    if [ -n "$IFCONFIG_IP" ]; then
        echo "方法3 (ifconfig):    $IFCONFIG_IP"
    fi
fi

echo ""
echo "=========================================="
echo "🌐 网络接口详情："
echo "=========================================="

# 显示所有网络接口
if command -v ip &> /dev/null; then
    ip -4 addr show | grep -E "^[0-9]+:|inet " | while read line; do
        if [[ $line =~ ^[0-9]+: ]]; then
            echo ""
            echo "$line"
        else
            echo "  $line"
        fi
    done
elif command -v ifconfig &> /dev/null; then
    ifconfig | grep -A 1 "^[a-z]"
fi

echo ""
echo "=========================================="
echo "📝 使用说明："
echo "=========================================="
echo ""
echo "1. 本地访问（同一台机器）："
echo "   curl http://127.0.0.1:8000/health"
echo "   或"
echo "   curl http://localhost:8000/health"
echo ""
echo "2. 局域网访问（同一网络的其他机器）："
echo "   使用上面显示的本机 IP 地址，例如："
if [ -n "$LOCAL_IP" ]; then
    echo "   curl http://$LOCAL_IP:8000/health"
else
    echo "   curl http://<你的本机IP>:8000/health"
fi
echo ""
echo "3. 公网访问（如果服务器有公网 IP）："
echo "   使用服务器的公网 IP 地址"
echo ""
echo "=========================================="
echo "🧪 测试连接："
echo "=========================================="
echo ""

# 测试本地连接
echo "测试本地连接 (127.0.0.1:8000)..."
if curl -s --connect-timeout 2 http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "✅ 本地连接成功！"
    echo "   响应："
    curl -s http://127.0.0.1:8000/health | head -5
else
    echo "❌ 本地连接失败（vLLM 服务可能未启动）"
fi

echo ""
echo "=========================================="

