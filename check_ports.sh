#!/bin/bash
# 端口检查脚本 - 查看本地端口占用情况

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  🔍 端口占用检查工具                                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 检查指定端口
check_port() {
    local port=$1
    echo "检查端口 $port..."
    
    # 方法1: 使用 netstat
    if command -v netstat >/dev/null 2>&1; then
        result=$(netstat -tlnp 2>/dev/null | grep ":$port ")
        if [ -n "$result" ]; then
            echo "  ✓ 端口 $port 正在使用"
            echo "  详情: $result"
            pid=$(echo "$result" | awk '{print $7}' | cut -d'/' -f1)
            if [ -n "$pid" ]; then
                echo "  进程信息:"
                ps -p "$pid" -o pid,user,cmd --no-headers 2>/dev/null | sed 's/^/    /'
            fi
            return 0
        fi
    fi
    
    # 方法2: 使用 ss
    if command -v ss >/dev/null 2>&1; then
        result=$(ss -tlnp 2>/dev/null | grep ":$port ")
        if [ -n "$result" ]; then
            echo "  ✓ 端口 $port 正在使用"
            echo "  详情: $result"
            return 0
        fi
    fi
    
    # 方法3: 使用 lsof
    if command -v lsof >/dev/null 2>&1; then
        result=$(lsof -i :$port 2>/dev/null)
        if [ -n "$result" ]; then
            echo "  ✓ 端口 $port 正在使用"
            echo "$result" | sed 's/^/  /'
            return 0
        fi
    fi
    
    # 方法4: 使用 /proc/net/tcp (Linux)
    if [ -f /proc/net/tcp ]; then
        hex_port=$(printf "%04X" $port)
        if grep -q ":$hex_port " /proc/net/tcp 2>/dev/null; then
            echo "  ✓ 端口 $port 正在使用（通过 /proc/net/tcp）"
            return 0
        fi
    fi
    
    echo "  ✗ 端口 $port 未使用"
    return 1
}

# 检查常用端口
PORTS=(7870 7871 7872 7860 8080 8000)

echo "检查常用端口:"
for port in "${PORTS[@]}"; do
    check_port "$port"
    echo ""
done

# 检查所有 Python/Gradio 相关进程
echo "═══════════════════════════════════════════════════════════════"
echo "Python/Gradio 相关进程:"
ps aux | grep -E '(gradio|python.*gradio|python.*787)' | grep -v grep | while read line; do
    echo "  $line"
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "快速命令:"
echo "  查看所有监听端口: netstat -tlnp | grep LISTEN"
echo "  查看特定端口:     lsof -i :7870"
echo "  杀死端口进程:     kill -9 \$(lsof -t -i :7870)"

