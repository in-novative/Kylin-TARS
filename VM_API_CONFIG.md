# 虚拟机 UITARS API 配置指南

## 为什么需要配置 UITARS_API_BASE？

记忆模块（Memory Module）需要调用 UITARS 推理服务来：
- 生成 System-2 推理链
- 检索相似任务轨迹
- 执行智能任务分解

在虚拟机环境中，UITARS 服务部署在远程服务器上，因此需要配置远程 API 地址。

---

## 配置方法

### 方法1：创建配置文件（推荐）

```bash
# 创建配置目录
mkdir -p ~/.config/kylin-gui-agent

# 创建配置文件（替换 YOUR_SERVER_IP 为实际服务器IP）
cat > ~/.config/kylin-gui-agent/api_config.sh << 'EOF'
#!/bin/bash
# UITARS API 配置
export UITARS_API_BASE="http://YOUR_SERVER_IP:8000"
EOF

# 赋予执行权限
chmod +x ~/.config/kylin-gui-agent/api_config.sh
```

**重要**：将 `YOUR_SERVER_IP` 替换为实际的 UITARS 服务器 IP 地址。

**示例**：
```bash
export UITARS_API_BASE="http://192.168.1.100:8000"
```

---

### 方法2：设置环境变量（临时）

```bash
# 在当前终端会话中设置
export UITARS_API_BASE="http://YOUR_SERVER_IP:8000"

# 然后运行启动脚本
./run_KL.sh
```

**注意**：这种方法只在当前终端会话有效，关闭终端后需要重新设置。

---

### 方法3：在虚拟环境激活脚本中设置（永久）

```bash
# 编辑虚拟环境激活脚本
nano venv/bin/activate

# 在文件末尾添加：
export UITARS_API_BASE="http://YOUR_SERVER_IP:8000"

# 保存后，每次激活虚拟环境都会自动设置
source venv/bin/activate
```

---

## 验证配置

### 1. 检查环境变量

```bash
echo $UITARS_API_BASE
# 应该输出: http://YOUR_SERVER_IP:8000
```

### 2. 测试 API 连接

```bash
# 测试 API 是否可达
curl http://YOUR_SERVER_IP:8000/health

# 或测试 API 端点
curl http://YOUR_SERVER_IP:8000/v1/models
```

### 3. 启动服务时检查

运行 `./run_KL.sh` 时，如果配置正确，会看到：
```
UITARS_API_BASE: http://YOUR_SERVER_IP:8000 (远程API)
```

如果未配置，会看到警告：
```
[警告] UITARS_API_BASE 未正确配置，记忆模块将无法使用
```

---

## 常见问题

### Q1: 如何找到 UITARS 服务器的 IP 地址？

**A**: 询问服务器管理员，或查看服务器配置文档。

### Q2: 端口号是多少？

**A**: 默认是 `8000`，如果服务器使用了其他端口，请相应修改。

### Q3: 配置后记忆模块仍然无法使用？

**A**: 请检查：
1. 环境变量是否正确设置：`echo $UITARS_API_BASE`
2. 网络连接是否正常：`ping YOUR_SERVER_IP`
3. API 服务是否运行：`curl http://YOUR_SERVER_IP:8000/health`
4. 防火墙是否阻止连接

### Q4: 如何确认记忆模块是否可用？

**A**: 在 Web UI 中：
1. 勾选"使用记忆模块"复选框
2. 输入一个任务
3. 如果记忆模块可用，会看到推理链生成和记忆检索的过程
4. 如果不可用，会直接使用关键词匹配模式（降级策略）

---

## 配置示例

### 示例1：服务器 IP 为 192.168.1.100，端口 8000

```bash
export UITARS_API_BASE="http://192.168.1.100:8000"
```

### 示例2：服务器 IP 为 10.0.0.50，端口 8080

```bash
export UITARS_API_BASE="http://10.0.0.50:8080"
```

### 示例3：使用 HTTPS（如果服务器支持）

```bash
export UITARS_API_BASE="https://uitars.example.com:8443"
```

---

## 配置检查清单

在启动服务前，请确认：

- [ ] UITARS 服务器 IP 地址已知
- [ ] UITARS 服务器端口号已知
- [ ] 网络连接正常（可以 ping 通服务器）
- [ ] API 服务可访问（可以 curl 测试）
- [ ] 环境变量已正确设置
- [ ] 配置文件已创建（如果使用方法1）

---

## 相关文档

- `VM_ENVIRONMENT_SETUP.md` - 虚拟机环境配置指南
- `VM_TROUBLESHOOTING.md` - 问题排查指南
- `run_KL_README.md` - 启动脚本说明

