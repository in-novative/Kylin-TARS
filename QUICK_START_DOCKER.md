# Kylin-TARS Docker 快速开始指南

本指南提供最快速的部署方式，适合熟悉 Docker 的用户。

## 🚀 三步快速部署

### 第一步：构建镜像

```bash
cd /data1/cyx/Kylin-TARS
./build_docker_openkylin.sh
```

**预计时间**：10-30 分钟（首次构建）

### 第二步：启动容器

```bash
./start_docker_openkylin.sh
```

**输出信息**：
- 容器名称：`kylin-tars-openkylin`
- VNC 端口：`5900`
- Gradio UI 端口：`7870`

### 第三步：连接和使用

#### 方式 A：通过 VNC 连接桌面（推荐）

1. **安装 VNC Viewer**：
   - Windows/Mac: https://www.realvnc.com/en/connect/download/viewer/
   - Linux: `sudo apt install tigervnc-viewer`

2. **连接**：
   - 地址：`<服务器IP>:5900`
   - 密码：`123456`（默认，建议修改）

3. **在桌面中启动项目**：
   ```bash
   # 打开终端
   cd ~/kylin-tars-project
   ./start_upgrade.sh
   ```

4. **访问 Web UI**：
   - 在桌面浏览器打开：`http://localhost:7870`

#### 方式 B：通过 SSH 进入容器

```bash
# 进入容器
docker exec -it kylin-tars-openkylin bash
su kylin-user

# 安装项目依赖（首次）
cd ~/kylin-tars-project
bash install_in_container.sh

# 启动项目
./start_upgrade.sh
```

---

## 📋 常用操作

### 查看容器状态

```bash
docker ps | grep kylin-tars-openkylin
```

### 查看日志

```bash
docker logs -f kylin-tars-openkylin
```

### 停止容器

```bash
docker stop kylin-tars-openkylin
```

### 重启容器

```bash
docker restart kylin-tars-openkylin
```

### 删除容器（重新开始）

```bash
docker stop kylin-tars-openkylin
docker rm kylin-tars-openkylin
```

---

## ⚙️ 自定义配置

### 修改 VNC 密码

```bash
docker exec -it kylin-tars-openkylin bash
su kylin-user
vncpasswd
# 输入新密码
exit
exit

# 重启容器使配置生效
docker restart kylin-tars-openkylin
```

### 修改 VNC 分辨率

编辑 `start_docker_openkylin.sh`，修改 `VNC_GEOMETRY` 环境变量：

```bash
-e VNC_GEOMETRY=2560x1440  # 改为你需要的分辨率
```

### 禁用 VNC（仅 SSH 访问）

```bash
export ENABLE_VNC=false
./start_docker_openkylin.sh
```

---

## 🔧 故障排查

### 问题 1：无法连接 VNC

**检查清单**：
- [ ] 容器是否运行：`docker ps`
- [ ] 端口是否开放：`netstat -tlnp | grep 5900`
- [ ] 防火墙是否允许：`sudo ufw status`
- [ ] VNC 服务是否启动：`docker logs kylin-tars-openkylin | grep VNC`

### 问题 2：项目启动失败

**检查清单**：
- [ ] 进入容器检查依赖：`docker exec -it kylin-tars-openkylin bash`
- [ ] 运行安装脚本：`bash install_in_container.sh`
- [ ] 检查 Python 版本：`python3 --version`（需要 3.10+）
- [ ] 查看详细错误：`docker logs kylin-tars-openkylin`

### 问题 3：桌面卡顿

**解决方案**：
- 增加共享内存：修改 `--shm-size=4g`
- 降低分辨率：修改 `VNC_GEOMETRY=1280x720`
- 检查服务器资源：`docker stats kylin-tars-openkylin`

---

## 📚 更多信息

- **详细部署文档**：`DOCKER_DEPLOYMENT_OPENKYLIN.md`
- **项目文档**：`README_UPGRADE.md`
- **功能检查**：`FUNCTION_CHECK_REPORT.md`

---

**提示**：首次部署建议阅读完整文档 `DOCKER_DEPLOYMENT_OPENKYLIN.md` 以了解所有配置选项。

