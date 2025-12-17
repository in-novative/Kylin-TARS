# 虚拟机网络连接问题排查指南

## 错误信息分析

```
curl: (7) Failed to connect to 192.168.153.115 port 8000 after 21027 ms: Couldn't connect to server
```

这个错误表示：
- **错误代码 7**：无法连接到服务器
- **超时时间**：21秒后放弃连接
- **可能原因**：网络不通、服务器未运行、防火墙阻止、端口未开放

---

## 排查步骤

### 1. 检查网络连通性

```bash
# 测试是否能 ping 通服务器
ping -c 4 192.168.153.115

# 如果 ping 不通，检查：
# - 虚拟机网络配置（NAT/桥接模式）
# - 服务器 IP 是否正确
# - 是否在同一网络
```

**预期结果**：
- ✅ 能 ping 通：网络层连接正常
- ❌ 不能 ping 通：网络配置问题

---

### 2. 检查端口是否开放

```bash
# 使用 telnet 测试端口（如果没有 telnet，使用 nc）
telnet 192.168.153.115 8000

# 或使用 nc (netcat)
nc -zv 192.168.153.115 8000

# 或使用 timeout + bash
timeout 5 bash -c "</dev/tcp/192.168.153.115/8000" && echo "端口开放" || echo "端口关闭"
```

**预期结果**：
- ✅ 端口开放：可以建立 TCP 连接
- ❌ 端口关闭：服务器未运行或防火墙阻止

---

### 3. 检查服务器状态

**在服务器上检查**：

```bash
# 检查服务是否运行
ps aux | grep -E "vllm|uitars|8000"

# 检查端口监听状态
netstat -tlnp | grep 8000
# 或
ss -tlnp | grep 8000

# 检查服务日志
# 根据实际服务查看日志
```

---

### 4. 检查防火墙规则

**在服务器上检查**：

```bash
# Ubuntu/Debian/Kylin
sudo ufw status
sudo iptables -L -n | grep 8000

# 如果需要开放端口
sudo ufw allow 8000/tcp
sudo ufw reload
```

**在虚拟机上检查**：

```bash
# 检查虚拟机防火墙
sudo ufw status
```

---

### 5. 检查虚拟机网络配置

```bash
# 查看虚拟机网络配置
ip addr show
# 或
ifconfig

# 查看路由表
ip route
# 或
route -n

# 测试 DNS（如果使用域名）
nslookup 192.168.153.115
```

---

### 6. 检查虚拟机网络模式

**VMware/VirtualBox 网络模式**：

1. **NAT 模式**：
   - 虚拟机通过主机 NAT 访问外网
   - 可能无法直接访问局域网其他主机
   - **解决方案**：改为桥接模式

2. **桥接模式**：
   - 虚拟机直接连接到物理网络
   - 可以访问同一网段的其他主机
   - **推荐**：使用桥接模式

3. **仅主机模式**：
   - 只能访问主机
   - 无法访问局域网其他主机

---

## 常见问题解决方案

### 问题1：虚拟机无法 ping 通服务器

**可能原因**：
- 虚拟机网络模式不正确（NAT 模式）
- 不在同一网段
- 网络配置错误

**解决方案**：
1. 将虚拟机网络模式改为**桥接模式**
2. 检查 IP 地址是否在同一网段
3. 检查虚拟机网络适配器设置

---

### 问题2：能 ping 通但端口不通

**可能原因**：
- 服务器防火墙阻止
- 服务器服务未运行
- 端口被其他程序占用

**解决方案**：
1. 在服务器上检查防火墙规则
2. 确认服务正在运行
3. 检查端口监听状态

---

### 问题3：服务器防火墙阻止

**解决方案**：

```bash
# 在服务器上执行
sudo ufw allow 8000/tcp
sudo ufw reload

# 或使用 iptables
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
sudo iptables-save
```

---

### 问题4：服务器服务未运行

**解决方案**：

```bash
# 在服务器上启动服务
# 根据实际服务启动命令
cd /path/to/Kylin-TARS
./start_vllm_remote_api.sh
# 或
python -m vllm.entrypoints.openai.api_server --model /data1/models/UI-TARS-1.5-7B --port 8000
```

---

## 快速诊断脚本

在虚拟机上运行以下脚本：

```bash
#!/bin/bash
SERVER_IP="192.168.153.115"
SERVER_PORT="8000"

echo "=== 网络连接诊断 ==="
echo ""

echo "1. 测试网络连通性..."
if ping -c 2 -W 2 $SERVER_IP &> /dev/null; then
    echo "   ✅ 可以 ping 通服务器"
else
    echo "   ❌ 无法 ping 通服务器"
    echo "   建议：检查虚拟机网络模式（应使用桥接模式）"
    exit 1
fi

echo ""
echo "2. 测试端口连通性..."
if timeout 5 bash -c "</dev/tcp/$SERVER_IP/$SERVER_PORT" 2>/dev/null; then
    echo "   ✅ 端口 $SERVER_PORT 开放"
else
    echo "   ❌ 端口 $SERVER_PORT 关闭或无法访问"
    echo "   建议："
    echo "   - 检查服务器服务是否运行"
    echo "   - 检查服务器防火墙规则"
    echo "   - 检查服务器端口监听状态"
    exit 1
fi

echo ""
echo "3. 测试 API 连接..."
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
    -X POST http://$SERVER_IP:$SERVER_PORT/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"test","messages":[{"role":"user","content":"test"}]}')

if [ "$API_RESPONSE" = "200" ] || [ "$API_RESPONSE" = "400" ] || [ "$API_RESPONSE" = "422" ]; then
    echo "   ✅ API 服务可访问（HTTP $API_RESPONSE）"
else
    echo "   ⚠️  API 服务响应异常（HTTP $API_RESPONSE）"
    echo "   建议：检查 API 服务状态和配置"
fi

echo ""
echo "=== 诊断完成 ==="
```

---

## 依赖检查

根据你的 `pip list` 输出，**所有必要的依赖都已安装**，包括：
- ✅ `requests` - HTTP 请求库
- ✅ `httpx` - 异步 HTTP 客户端
- ✅ `openai` - OpenAI API 客户端

**结论**：这不是依赖问题，是网络连接问题。

---

## 推荐解决方案

### 方案1：检查虚拟机网络模式（最可能）

1. **VMware**：
   - 虚拟机设置 → 网络适配器 → 桥接模式
   - 或：NAT 模式 + 端口转发

2. **VirtualBox**：
   - 设置 → 网络 → 适配器1 → 桥接网卡

3. **重启网络**：
   ```bash
   sudo systemctl restart networking
   # 或
   sudo ifdown eth0 && sudo ifup eth0
   ```

### 方案2：在服务器上检查服务状态

```bash
# 在服务器上执行
# 检查服务是否运行
ps aux | grep vllm

# 检查端口监听
netstat -tlnp | grep 8000

# 如果服务未运行，启动服务
cd /path/to/Kylin-TARS
./start_vllm_remote_api.sh
```

### 方案3：配置端口转发（如果使用 NAT 模式）

如果必须使用 NAT 模式，可以配置端口转发：
- VMware：虚拟机设置 → 网络适配器 → NAT → 高级 → 端口转发
- VirtualBox：设置 → 网络 → 高级 → 端口转发

---

## 验证配置

配置完成后，运行诊断脚本验证：

```bash
# 保存上面的诊断脚本为 check_network.sh
chmod +x check_network.sh
./check_network.sh
```

如果所有检查通过，再次尝试 curl 命令：

```bash
curl -X POST http://192.168.153.115:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "/data1/models/UI-TARS-1.5-7B",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 50
  }'
```

