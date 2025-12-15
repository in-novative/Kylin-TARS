# Kylin-TARS Docker快速开始指南

## 🚀 5分钟快速部署

### 前置条件
- Linux服务器（Ubuntu/CentOS/Debian）
- Docker已安装
- （可选）NVIDIA GPU + nvidia-container-toolkit

### 快速部署步骤

#### 1. 克隆/准备项目
```bash
cd /opt
# 假设项目已在此目录
cd kylin-tars
```

#### 2. 构建镜像
```bash
docker build \
  --build-arg USER_ID=$(id -u) \
  --build-arg GROUP_ID=$(id -g) \
  -f Dockerfile.kylin \
  -t kylin-tars:latest \
  .
```

#### 3. 启动容器
```bash
docker-compose -f docker-compose.kylin.yml up -d
```

#### 4. 查看日志
```bash
docker-compose -f docker-compose.kylin.yml logs -f
```

#### 5. 访问服务
- **VNC桌面**: `服务器IP:5900` (密码: kylin123)
- **Gradio UI**: `http://服务器IP:7870`

### 常用命令

```bash
# 启动
docker-compose -f docker-compose.kylin.yml up -d

# 停止
docker-compose -f docker-compose.kylin.yml down

# 重启
docker-compose -f docker-compose.kylin.yml restart

# 查看日志
docker-compose -f docker-compose.kylin.yml logs -f

# 进入容器
docker exec -it kylin-tars-container /bin/bash

# 测试
./test_docker_kylin.sh
```

### 故障排查

如果遇到问题，请查看详细文档：
- [完整部署指南](DOCKER_DEPLOYMENT_KYLIN.md)
- [迁移计划](DOCKER_MIGRATION_PLAN.md)

### 下一步

1. 修改VNC密码（安全）
2. 配置防火墙规则
3. 配置GPU支持（如果需要）
4. 配置数据备份

