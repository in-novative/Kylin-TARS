# API Key 和模型名称配置指南

## 问题说明

当使用外部 API（如 `https://xiaoai.plus/v1`）时，需要：
1. **API Key**：用于身份验证（401 Unauthorized 错误的原因）
2. **正确的模型名称**：外部 API 使用模型名称（如 `gpt-4o`），而不是本地模型路径

---

## 配置方法

### 方法1：环境变量配置（推荐）

```bash
# 设置 API 地址
export UITARS_API_BASE="https://xiaoai.plus/v1"

# 设置 API Key（支持多个环境变量名）
export UITARS_API_KEY="sk-lgW2a38mNKdL3lAfKnjQ55yl3NujlfAwlg7u6GqjOfJXyOKU"
# 或
export OPENAI_API_KEY="sk-lgW2a38mNKdL3lAfKnjQ55yl3NujlfAwlg7u6GqjOfJXyOKU"
# 或
export API_KEY="sk-lgW2a38mNKdL3lAfKnjQ55yl3NujlfAwlg7u6GqjOfJXyOKU"

# 设置模型名称（外部 API 使用模型名称，不是路径）
export UITARS_MODEL_NAME="gpt-4o"
# 或
export VLLM_MODEL_NAME="gpt-4o"
```

### 方法2：配置文件（永久配置）

创建配置文件 `~/.config/kylin-gui-agent/api_config.sh`：

```bash
mkdir -p ~/.config/kylin-gui-agent

cat > ~/.config/kylin-gui-agent/api_config.sh << 'EOF'
#!/bin/bash
# UITARS API 配置

# API 地址
export UITARS_API_BASE="https://xiaoai.plus/v1"

# API Key
export UITARS_API_KEY="sk-lgW2a38mNKdL3lAfKnjQ55yl3NujlfAwlg7u6GqjOfJXyOKU"

# 模型名称（外部 API 使用模型名称）
export UITARS_MODEL_NAME="gpt-4o"
EOF

chmod +x ~/.config/kylin-gui-agent/api_config.sh
```

然后在启动前加载配置：
```bash
source ~/.config/kylin-gui-agent/api_config.sh
./run_KL.sh
```

### 方法3：在 run_KL.sh 中设置

编辑 `run_KL.sh`，在启动服务前添加：

```bash
# API 配置
export UITARS_API_BASE="https://xiaoai.plus/v1"
export UITARS_API_KEY="sk-lgW2a38mNKdL3lAfKnjQ55yl3NujlfAwlg7u6GqjOfJXyOKU"
export UITARS_MODEL_NAME="gpt-4o"
```

---

## 环境变量优先级

### API Key 优先级（按顺序检查）
1. `UITARS_API_KEY`（最高优先级）
2. `OPENAI_API_KEY`
3. `API_KEY`

### 模型名称优先级
- 如果设置了 `UITARS_API_BASE`（使用外部 API）：
  - `UITARS_MODEL_NAME`（优先）
  - `VLLM_MODEL_NAME`（备选）
  - 默认：`gpt-4o`
- 如果使用本地 vLLM：
  - `VLLM_MODEL_NAME`
  - 默认：`/data1/models/UI-TARS-1.5-7B`

---

## 验证配置

### 1. 检查环境变量

```bash
echo "API Base: $UITARS_API_BASE"
echo "API Key: ${UITARS_API_KEY:0:20}..."  # 只显示前20个字符
echo "Model: $UITARS_MODEL_NAME"
```

### 2. 测试 API 调用

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://xiaoai.plus/v1",
    api_key="sk-lgW2a38mNKdL3lAfKnjQ55yl3NujlfAwlg7u6GqjOfJXyOKU"
)

completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "测试"}]
)
print(completion.choices[0].message.content)
```

### 3. 检查日志

运行 `./run_KL.sh` 后，查看日志：
- ✅ 成功：看到推理链生成成功
- ❌ 401 错误：API Key 未设置或错误
- ❌ 404 错误：模型名称错误或 API 地址错误

---

## 常见问题

### Q1: 401 Unauthorized 错误

**原因**：API Key 未设置或错误

**解决方案**：
```bash
export UITARS_API_KEY="your-api-key"
```

### Q2: 模型名称错误

**原因**：外部 API 使用模型名称（如 `gpt-4o`），而不是本地模型路径

**解决方案**：
```bash
export UITARS_MODEL_NAME="gpt-4o"
```

### Q3: 如何知道应该使用哪个模型名称？

**A**: 查看 API 提供商的文档，或测试：
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://xiaoai.plus/v1/models
```

### Q4: 本地 vLLM 和外部 API 的区别

| 项目 | 本地 vLLM | 外部 API |
|------|----------|---------|
| API 地址 | `http://localhost:8000` | `https://xiaoai.plus/v1` |
| 模型名称 | 模型路径（如 `/data1/models/UI-TARS-1.5-7B`） | 模型名称（如 `gpt-4o`） |
| API Key | 通常不需要 | 需要 |
| 环境变量 | `VLLM_API_BASE` | `UITARS_API_BASE` |

---

## 配置示例

### 示例1：使用 xiaoai.plus API

```bash
export UITARS_API_BASE="https://xiaoai.plus/v1"
export UITARS_API_KEY="sk-lgW2a38mNKdL3lAfKnjQ55yl3NujlfAwlg7u6GqjOfJXyOKU"
export UITARS_MODEL_NAME="gpt-4o"
```

### 示例2：使用 OpenAI API

```bash
export UITARS_API_BASE="https://api.openai.com/v1"
export OPENAI_API_KEY="sk-..."
export UITARS_MODEL_NAME="gpt-4o"
```

### 示例3：使用本地 vLLM

```bash
export VLLM_API_BASE="http://localhost:8000"
export VLLM_MODEL_NAME="/data1/models/UI-TARS-1.5-7B"
# 不需要 API Key
```

---

## 相关文档

- `VM_API_CONFIG.md` - API 配置指南
- `API_URL_FIX.md` - API URL 修复说明
- `run_KL_README.md` - 启动脚本说明

