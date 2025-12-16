#!/bin/bash
# vLLM UITARS 远程 API 服务启动脚本
# 
# 功能：
# 1. 启动 vLLM OpenAI API 服务器，允许远程访问
# 2. 可选：配置 Nginx 反向代理（提供 HTTPS）
# 3. 可选：添加 API Key 认证

set -e

# ============================================================
# 配置参数
# ============================================================

# 模型路径
MODEL_PATH="${MODEL_PATH:-/data1/models/UI-TARS-1.5-7B}"

# API 服务器配置
HOST="${VLLM_HOST:-0.0.0.0}"  # 0.0.0.0 允许远程访问，127.0.0.1 仅本地
PORT="${VLLM_PORT:-8000}"
API_KEY="${VLLM_API_KEY:-}"  # 可选：设置 API Key 进行认证

# vLLM 参数
DTYPE="${VLLM_DTYPE:-bfloat16}"
MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-8192}"
GPU_MEMORY_UTIL="${VLLM_GPU_MEMORY_UTIL:-0.7}"

# ============================================================
# 启动 vLLM API 服务器
# ============================================================

echo "=========================================="
echo "启动 vLLM UITARS 远程 API 服务"
echo "=========================================="
echo "模型路径: $MODEL_PATH"
echo "监听地址: $HOST:$PORT"
echo "数据类型: $DTYPE"
echo "最大模型长度: $MAX_MODEL_LEN"
echo "GPU 内存利用率: $GPU_MEMORY_UTIL"
echo "=========================================="

# 构建启动命令
CMD="python -m vllm.entrypoints.openai.api_server"
CMD="$CMD --model $MODEL_PATH"
CMD="$CMD --trust-remote-code"
CMD="$CMD --dtype $DTYPE"
CMD="$CMD --max-model-len $MAX_MODEL_LEN"
CMD="$CMD --gpu-memory-utilization $GPU_MEMORY_UTIL"
CMD="$CMD --host $HOST"
CMD="$CMD --port $PORT"

# 如果设置了 API Key，添加认证
if [ -n "$API_KEY" ]; then
    echo "⚠️  已启用 API Key 认证"
    CMD="$CMD --api-key $API_KEY"
fi

echo ""
echo "执行命令:"
echo "$CMD"
echo ""

# 启动服务
exec $CMD

