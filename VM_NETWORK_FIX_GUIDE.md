# 虚拟机网络连接修复指南

## 问题确认

诊断结果显示：**无法 ping 通服务器**，这是网络连通性问题。

**根本原因**：虚拟机网络模式配置不正确，无法访问局域网其他主机。

---

## 解决方案

### 方案1：修改虚拟机网络模式为桥接模式（推荐）

#### VMware 虚拟机

**步骤1：关闭虚拟机**

```bash
# 在虚拟机中执行
sudo shutdown -h now
```

**步骤2：修改网络设置**

1. 在 VMware 中，右键点击虚拟机 → **设置**
2. 选择 **网络适配器**
3. 网络连接选择 **桥接模式**
4. 如果有多块网卡，选择连接到物理网络的网卡
5. 点击 **确定**

**步骤3：启动虚拟机并检查网络**

```bash
# 启动虚拟机后，检查网络配置
ip addr show
# 或
ifconfig

# 查看 IP 地址是否与服务器在同一网段
# 例如：如果服务器是 192.168.153.115
# 虚拟机应该获得类似 192.168.153.xxx 的 IP
```

**步骤4：重新测试连接**

```bash
# 测试 ping
ping -c 4 192.168.153.115

# 如果 ping 通，测试端口
./check_network.sh 192.168.153.115 8000
```

---

#### VirtualBox 虚拟机

**步骤1：关闭虚拟机**

```bash
sudo shutdown -h now
```

**步骤2：修改网络设置**

1. 在 VirtualBox 中，右键点击虚拟机 → **设置**
2. 选择 **网络**
3. 适配器1 → 启用网络连接
4. 连接方式选择 **桥接网卡**
5. 界面名称选择连接到物理网络的网卡
6. 点击 **确定**

**步骤3：启动虚拟机并检查网络**

```bash
# 启动虚拟机后，检查网络配置
ip addr show

# 如果 IP 地址未自动获取，手动配置
sudo dhclient
# 或手动设置（根据实际情况）
sudo ip addr add 192.168.153.xxx/24 dev eth0
sudo ip route add default via 192.168.153.1
```

**步骤4：重新测试连接**

```bash
ping -c 4 192.168.153.115
./check_network.sh 192.168.153.115 8000
```

---

### 方案2：检查当前网络配置

在修改网络模式前，先检查当前配置：

```bash
# 查看当前网络接口
ip addr show

# 查看路由表
ip route

# 查看网关
ip route | grep default

# 查看 DNS
cat /etc/resolv.conf
```

**判断标准**：
- 如果虚拟机 IP 是 `192.168.153.xxx`（与服务器同网段）→ 网络配置正确
- 如果虚拟机 IP 是 `192.168.xxx.xxx`（不同网段）或 `10.0.2.xxx`（NAT 模式）→ 需要修改

---

### 方案3：如果无法使用桥接模式（临时方案）

如果由于网络环境限制无法使用桥接模式，可以使用端口转发：

#### VMware NAT 端口转发

1. 虚拟机设置 → 网络适配器 → NAT → **高级** → **端口转发**
2. 添加规则：
   - 主机端口：`8000`
   - 类型：`TCP`
   - 虚拟机 IP：`192.168.153.115`
   - 虚拟机端口：`8000`
3. 在虚拟机中使用 `localhost:8000` 访问

**注意**：这种方法需要修改配置，将 `UITARS_API_BASE` 设置为 `http://localhost:8000`

---

## 验证步骤

### 1. 检查网络模式是否已修改

```bash
# 查看 IP 地址
ip addr show | grep "inet "

# 应该看到类似：
# inet 192.168.153.xxx/24 ...
# 与服务器 IP 192.168.153.115 在同一网段
```

### 2. 测试网络连通性

```bash
# 测试 ping
ping -c 4 192.168.153.115

# 应该看到：
# 4 packets transmitted, 4 received, 0% packet loss
```

### 3. 运行完整诊断

```bash
./check_network.sh 192.168.153.115 8000
```

**预期结果**：
- ✅ 可以 ping 通服务器
- ✅ 端口 8000 开放
- ✅ API 服务可访问

---

## 常见问题

### Q1: 修改网络模式后无法获取 IP 地址

**解决方案**：

```bash
# 重启网络服务
sudo systemctl restart networking

# 或手动获取 IP
sudo dhclient

# 或手动配置（根据实际情况）
sudo ip addr add 192.168.153.xxx/24 dev eth0
sudo ip route add default via 192.168.153.1
```

### Q2: 桥接模式后无法访问外网

**解决方案**：
- 检查物理网络是否允许访问外网
- 检查 DNS 配置：`cat /etc/resolv.conf`
- 测试 DNS：`nslookup www.baidu.com`

### Q3: 修改后仍然无法 ping 通

**可能原因**：
1. 服务器防火墙阻止 ICMP（ping）
2. 服务器 IP 地址不正确
3. 不在同一物理网络

**排查步骤**：

```bash
# 1. 检查服务器 IP 是否正确
# 在服务器上执行
ip addr show

# 2. 检查服务器防火墙
# 在服务器上执行
sudo ufw status

# 3. 测试其他端口
telnet 192.168.153.115 22  # SSH 端口
```

---

## 快速修复脚本

如果网络模式已修改但 IP 未更新，运行：

```bash
#!/bin/bash
# 重启网络配置

echo "重启网络服务..."
sudo systemctl restart networking

echo "等待 5 秒..."
sleep 5

echo "检查网络配置..."
ip addr show | grep "inet "

echo "测试连接..."
ping -c 2 192.168.153.115
```

---

## 配置 UITARS_API_BASE

网络连接正常后，配置 API 地址：

```bash
# 方法1：创建配置文件（推荐）
mkdir -p ~/.config/kylin-gui-agent
cat > ~/.config/kylin-gui-agent/api_config.sh << 'EOF'
#!/bin/bash
export UITARS_API_BASE="http://192.168.153.115:8000"
EOF
chmod +x ~/.config/kylin-gui-agent/api_config.sh

# 方法2：设置环境变量（临时）
export UITARS_API_BASE="http://192.168.153.115:8000"

# 验证配置
echo $UITARS_API_BASE
```

---

## 总结

**当前状态**：无法 ping 通服务器 → 网络连通性问题

**解决步骤**：
1. ✅ 修改虚拟机网络模式为桥接模式
2. ✅ 重启虚拟机或网络服务
3. ✅ 验证网络配置（IP 地址应在同一网段）
4. ✅ 重新运行诊断脚本验证连接
5. ✅ 配置 UITARS_API_BASE

**预期结果**：
- 可以 ping 通服务器
- 可以访问 API 服务
- 记忆模块可以正常使用

