# API URL 配置修复说明

## 问题描述

在使用外部 API（如 `https://xiaoai.plus/v1`）时，API 调用失败，错误信息显示：
```
404 Client Error: Not Found for url: https://xiaoai.plus/v1/v1/chat/completions
```

**原因**：URL 中出现了重复的 `/v1/v1/`，这是因为代码在构建 URL 时没有检查 `API_BASE` 是否已经包含了 `/v1` 路径。

---

## 修复内容

### 修复位置

`run/system2_prompt.py` 中的 `call_vllm_api()` 函数：

**修复前**：
```python
url = f"{API_BASE}/v1/chat/completions"
```

**修复后**：
```python
# 构建 API URL，避免重复 /v1
api_base = API_BASE.rstrip('/')
if api_base.endswith('/v1'):
    url = f"{api_base}/chat/completions"
else:
    url = f"{api_base}/v1/chat/completions"
```

---

## 配置说明

### 正确的 API_BASE 配置格式

#### 情况1：API 基础地址不包含 `/v1`
```bash
export UITARS_API_BASE="http://192.168.153.115:8000"
# 最终 URL: http://192.168.153.115:8000/v1/chat/completions
```

#### 情况2：API 基础地址已包含 `/v1`
```bash
export UITARS_API_BASE="https://xiaoai.plus/v1"
# 最终 URL: https://xiaoai.plus/v1/chat/completions（不会重复）
```

---

## 验证方法

### 1. 检查环境变量
```bash
echo $UITARS_API_BASE
```

### 2. 测试 API 调用
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://xiaoai.plus/v1",  # 或您的 API 地址
    api_key="your-api-key"
)

completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "测试"}]
)
print(completion.choices[0].message.content)
```

### 3. 检查日志
运行 `./run_KL.sh` 后，查看日志中是否有 API 调用成功的消息。

---

## 常见问题

### Q1: 如何知道我的 API 地址是否包含 `/v1`？

**A**: 查看 API 提供商的文档，或测试：
```bash
# 如果包含 /v1
curl https://xiaoai.plus/v1/models

# 如果不包含 /v1
curl http://192.168.153.115:8000/v1/models
```

### Q2: 修复后仍然失败？

**A**: 请检查：
1. 环境变量是否正确设置：`echo $UITARS_API_BASE`
2. API 地址是否可访问：`curl $UITARS_API_BASE/health` 或 `curl $UITARS_API_BASE/v1/models`
3. API Key 是否正确（如果 API 需要认证）
4. 网络连接是否正常

### Q3: 如何确认修复生效？

**A**: 运行推理任务，查看日志：
- ✅ 成功：看到推理链生成成功
- ❌ 失败：看到 404 错误（URL 重复）或连接错误

---

## 相关文件

- `run/system2_prompt.py` - API 调用逻辑
- `VM_API_CONFIG.md` - API 配置指南
- `run_KL.sh` - 启动脚本（加载环境变量）

