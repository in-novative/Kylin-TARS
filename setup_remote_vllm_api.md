# 将本地 vLLM UITARS 封装为远程访问 API

## 📋 概述

将本地运行的 vLLM UITARS 服务配置为可以通过远程访问的 API，类似于 OpenAI API 的格式。

## 🚀 方法1：直接启动远程 API（最简单）

### 步骤1：修改启动命令

原来的命令（仅本地访问）：
```bash
python -m vllm.entrypoints.openai.api_server \
    --model /data1/models/UI-TARS-1.5-7B \
    --trust-remote-code \
    --dtype bfloat16 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.7 \
    --port 8000
```

修改后的命令（允许远程访问）：
```bash
python -m vllm.entrypoints.openai.api_server \
    --model /data1/models/UI-TARS-1.5-7B \
    --trust-remote-code \
    --dtype bfloat16 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.7 \
    --host 0.0.0.0 \          # 关键：改为 0.0.0.0 允许远程访问
    --port 8000
```

### 步骤2：使用启动脚本（推荐）

使用提供的启动脚本：

```bash
# 设置环境变量
export MODEL_PATH="/data1/models/UI-TARS-1.5-7B"
export VLLM_HOST="0.0.0.0"  # 允许远程访问
export VLLM_PORT="8000"

# 可选：设置 API Key 进行认证
export VLLM_API_KEY="your-secret-api-key"

# 启动服务
chmod +x start_vllm_remote_api.sh
./start_vllm_remote_api.sh
```

### 步骤3：配置防火墙

如果服务器有防火墙，需要开放端口：

```bash
# Ubuntu/Debian
sudo ufw allow 8000/tcp

# CentOS/RHEL
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

### 步骤4：测试远程访问

从远程机器测试：

```bash
# 替换为你的服务器 IP
curl http://YOUR_SERVER_IP:8000/health
```

## 🔒 方法2：使用 Nginx 反向代理（推荐用于生产环境）

### 优势

1. **HTTPS 支持**：提供安全的 HTTPS 连接
2. **负载均衡**：可以配置多个后端实例
3. **认证管理**：在 Nginx 层面统一管理认证
4. **日志记录**：统一的访问日志

### 步骤1：安装 Nginx

```bash
sudo apt update
sudo apt install nginx
```

### 步骤2：配置 Nginx

创建配置文件 `/etc/nginx/sites-available/vllm-api`：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名或 IP

    # 如果需要 HTTPS，取消注释以下配置
    # listen 443 ssl;
    # ssl_certificate /path/to/cert.pem;
    # ssl_certificate_key /path/to/key.pem;

    # API Key 认证（可选）
    # 在 Nginx 层面添加 Basic Auth
    # auth_basic "Restricted";
    # auth_basic_user_file /etc/nginx/.htpasswd;

    location /v1/ {
        proxy_pass http://127.0.0.1:8000/v1/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # 支持流式输出（如果需要）
        proxy_buffering off;
        proxy_cache off;
    }

    # 健康检查端点
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
    }
}
```

### 步骤3：启用配置

```bash
sudo ln -s /etc/nginx/sites-available/vllm-api /etc/nginx/sites-enabled/
sudo nginx -t  # 测试配置
sudo systemctl reload nginx
```

### 步骤4：启动 vLLM（仅本地监听）

```bash
# vLLM 只需要监听本地
python -m vllm.entrypoints.openai.api_server \
    --model /data1/models/UI-TARS-1.5-7B \
    --trust-remote-code \
    --dtype bfloat16 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.7 \
    --host 127.0.0.1 \  # 仅本地访问
    --port 8000
```

### 步骤5：测试远程访问

```bash
# 通过 Nginx 访问
curl http://YOUR_SERVER_IP/v1/models
curl http://YOUR_SERVER_IP/health
```

## 🔐 方法3：添加 API Key 认证

### 在 vLLM 层面添加认证

vLLM 支持 `--api-key` 参数：

```bash
python -m vllm.entrypoints.openai.api_server \
    --model /data1/models/UI-TARS-1.5-7B \
    --trust-remote-code \
    --dtype bfloat16 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.7 \
    --host 0.0.0.0 \
    --port 8000 \
    --api-key "your-secret-api-key"  # 添加 API Key
```

客户端使用时需要添加认证头：

```bash
curl -H "Authorization: Bearer your-secret-api-key" \
     http://YOUR_SERVER_IP:8000/v1/models
```

### 在 Nginx 层面添加认证

使用 HTTP Basic Auth：

```bash
# 安装 htpasswd 工具
sudo apt install apache2-utils

# 创建用户密码文件
sudo htpasswd -c /etc/nginx/.htpasswd username
# 输入密码

# 在 Nginx 配置中添加
auth_basic "Restricted";
auth_basic_user_file /etc/nginx/.htpasswd;
```

## 📝 客户端配置

### 在 Kylin-TARS 中使用远程 API

编辑 `run.sh` 或 `start_upgrade.sh`：

```bash
# 使用远程 vLLM API
export UITARS_API_BASE="http://YOUR_SERVER_IP:8000"
export VLLM_MODEL_NAME="/data1/models/UI-TARS-1.5-7B"

# 如果设置了 API Key
export VLLM_API_KEY="your-secret-api-key"
```

### 修改 system2_prompt.py 支持 API Key

如果需要支持 API Key 认证，修改 `/data1/cyx/Kylin-TARS/run/system2_prompt.py` 中的 `call_vllm_api` 函数：

```python
def call_vllm_api(
    messages: list,
    max_tokens: int = 1024,
    temperature: float = 0.05,
    timeout: int = 120,
    model_name: Optional[str] = None
) -> Optional[str]:
    url = f"{API_BASE}/v1/chat/completions"
    
    # 添加认证头（如果设置了 API Key）
    headers = {}
    api_key = os.getenv("VLLM_API_KEY") or os.getenv("API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    payload = {
        "model": model_name or MODEL_NAME,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"API调用失败: {e}")
        return None
```

## 🧪 测试远程 API

### 测试健康检查

```bash
curl http://YOUR_SERVER_IP:8000/health
```

### 测试模型列表

```bash
curl http://YOUR_SERVER_IP:8000/v1/models
```

### 测试聊天完成

```bash
curl -X POST http://YOUR_SERVER_IP:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "/data1/models/UI-TARS-1.5-7B",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "max_tokens": 100
  }'
```

## ⚠️ 安全注意事项

1. **防火墙配置**：只开放必要的端口
2. **API Key 保护**：使用强密码，定期更换
3. **HTTPS 加密**：生产环境建议使用 HTTPS
4. **访问限制**：可以配置 IP 白名单
5. **日志监控**：监控 API 访问日志，及时发现异常

## 📊 性能优化

1. **GPU 内存**：根据实际情况调整 `--gpu-memory-utilization`
2. **并发处理**：vLLM 自动处理并发请求
3. **超时设置**：根据模型响应时间调整超时参数
4. **负载均衡**：如果需要，可以启动多个实例并使用 Nginx 负载均衡

## 🔍 故障排查

### 无法远程访问

1. 检查防火墙是否开放端口
2. 检查 vLLM 是否监听 `0.0.0.0` 而不是 `127.0.0.1`
3. 检查网络连接

### API 调用失败

1. 检查 API Key 是否正确
2. 检查请求格式是否符合 OpenAI 兼容格式
3. 查看 vLLM 日志：`tail -f vllm.log`

### 性能问题

1. 检查 GPU 使用率：`nvidia-smi`
2. 调整 `--gpu-memory-utilization` 参数
3. 检查模型是否加载成功

## 📚 参考资源

- [vLLM 文档](https://docs.vllm.ai/)
- [vLLM OpenAI API 服务器](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html)
- [Nginx 反向代理配置](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)

