# UITARS API 替换为其他大模型 API 指南

## 📋 概述

UITARS API 使用的是 **OpenAI 兼容的 API 格式**，因此可以轻松替换为任何支持 OpenAI 兼容接口的大模型服务。

## 🔍 API 格式要求

### 当前 UITARS API 格式

**请求端点：**
```
POST {API_BASE}/v1/chat/completions
```

**请求格式：**
```json
{
  "model": "模型名称",
  "messages": [
    {"role": "system", "content": "系统提示词"},
    {"role": "user", "content": "用户输入"}
  ],
  "max_tokens": 1024,
  "temperature": 0.05
}
```

**响应格式：**
```json
{
  "choices": [
    {
      "message": {
        "content": "模型生成的文本"
      }
    }
  ]
}
```

## ✅ 兼容的大模型服务

以下大模型服务都支持 OpenAI 兼容的 API 格式，可以直接替换：

### 1. OpenAI GPT 系列
```bash
export UITARS_API_BASE="https://api.openai.com/v1"
export VLLM_MODEL_NAME="gpt-4"  # 或 gpt-3.5-turbo
```

### 2. 通义千问（Qwen）
```bash
export UITARS_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
export VLLM_MODEL_NAME="qwen-plus"  # 或 qwen-turbo, qwen-max
```

### 3. 文心一言（如果提供兼容接口）
```bash
export UITARS_API_BASE="https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat"
export VLLM_MODEL_NAME="ernie-bot"  # 或其他模型
```

### 4. Claude（如果提供兼容接口）
```bash
export UITARS_API_BASE="https://api.anthropic.com/v1"
export VLLM_MODEL_NAME="claude-3-opus"  # 或其他版本
```

### 5. 其他 OpenAI 兼容服务
- **LocalAI**：本地部署的 OpenAI 兼容服务
- **vLLM**：本地 vLLM 服务（默认）
- **Ollama**：如果配置了 OpenAI 兼容接口
- **AnyScale**：OpenAI 兼容的托管服务

## 🔧 配置方法

### 方法1：环境变量配置（推荐）

在启动脚本（`run.sh` 或 `start_upgrade.sh`）中添加：

```bash
# 使用外部大模型 API
export UITARS_API_BASE="https://api.openai.com/v1"
export VLLM_MODEL_NAME="gpt-4"

# 如果需要 API Key
export OPENAI_API_KEY="your-api-key-here"
```

### 方法2：修改代码配置

编辑 `/data1/cyx/Kylin-TARS/run/system2_prompt.py`：

```python
# 修改 API 配置
UITARS_API_BASE = os.getenv("UITARS_API_BASE", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("VLLM_MODEL_NAME", "gpt-4")
```

## 🔐 API Key 配置

如果目标 API 需要认证，需要修改 `call_vllm_api` 函数：

```python
def call_vllm_api(
    messages: list,
    max_tokens: int = 1024,
    temperature: float = 0.05,
    timeout: int = 120,
    model_name: Optional[str] = None
) -> Optional[str]:
    url = f"{API_BASE}/v1/chat/completions"
    
    # 添加认证头（如果需要）
    headers = {}
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
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

## 📝 格式限制说明

### 必须满足的要求

1. **端点格式**：必须支持 `/v1/chat/completions` 端点
2. **请求格式**：必须接受标准的 OpenAI 格式请求
   - `model`：模型名称
   - `messages`：消息列表（包含 role 和 content）
   - `max_tokens`：最大生成 token 数
   - `temperature`：温度参数

3. **响应格式**：必须返回标准的 OpenAI 格式响应
   - `choices[0].message.content`：生成的文本内容

### 可选的支持

- `top_p`：核采样参数
- `frequency_penalty`：频率惩罚
- `presence_penalty`：存在惩罚
- `stream`：流式输出（当前代码不支持）

## 🚀 使用示例

### 示例1：使用 OpenAI GPT-4

```bash
export UITARS_API_BASE="https://api.openai.com/v1"
export VLLM_MODEL_NAME="gpt-4"
export OPENAI_API_KEY="sk-..."

./run.sh
```

### 示例2：使用通义千问

```bash
export UITARS_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
export VLLM_MODEL_NAME="qwen-plus"
export DASHSCOPE_API_KEY="sk-..."

# 修改 system2_prompt.py 中的认证头
# headers["Authorization"] = f"Bearer {os.getenv('DASHSCOPE_API_KEY')}"
```

### 示例3：使用本地 vLLM（默认）

```bash
# 不设置 UITARS_API_BASE，使用默认的本地 vLLM
export VLLM_API_BASE="http://localhost:8000"
export VLLM_MODEL_NAME="/data1/models/UI-TARS-1.5-7B"

./run.sh
```

## ⚠️ 注意事项

1. **API Key 安全**：不要将 API Key 硬编码在代码中，使用环境变量
2. **速率限制**：注意目标 API 的速率限制，可能需要添加重试逻辑
3. **成本考虑**：使用商业 API 会产生费用，注意监控使用量
4. **响应时间**：不同 API 的响应时间可能不同，可能需要调整 timeout
5. **模型能力**：不同模型的推理能力不同，可能需要调整 prompt

## 🔍 测试 API 兼容性

可以使用以下 Python 脚本测试 API 是否兼容：

```python
import requests
import os

API_BASE = os.getenv("UITARS_API_BASE", "https://api.openai.com/v1")
API_KEY = os.getenv("OPENAI_API_KEY", "")

url = f"{API_BASE}/v1/chat/completions"
headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
payload = {
    "model": "gpt-3.5-turbo",
    "messages": [
        {"role": "user", "content": "Hello, world!"}
    ],
    "max_tokens": 100
}

response = requests.post(url, json=payload, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

## 📚 参考资源

- [OpenAI API 文档](https://platform.openai.com/docs/api-reference)
- [通义千问 API 文档](https://help.aliyun.com/zh/model-studio/)
- [vLLM 文档](https://docs.vllm.ai/)

